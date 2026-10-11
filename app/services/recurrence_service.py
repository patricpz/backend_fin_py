from __future__ import annotations

from uuid import UUID, uuid5, NAMESPACE_URL
from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.recurrence import RecurringTransaction
from app.models.transaction import Transaction
from app.repositories.recurrence_repository import RecurrenceRepository
from app.repositories.transaction_repository import TransactionRepository
from app.repositories.account_repository import AccountRepository
from app.repositories.category_repository import CategoryRepository
from app.schemas.recurrence import RecurrenceCreate, RecurrenceUpdate, RecurrenceGenerateResponse
from app.core.exceptions import NotFoundError, BusinessRuleError
from app.models.enums import TransactionType, TransactionStatus, RecurrenceFrequency


class RecurrenceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = RecurrenceRepository(db)
        self.tx_repo = TransactionRepository(db)
        self.account_repo = AccountRepository(db)
        self.cat_repo = CategoryRepository(db)

    async def _validate_account(self, user_id: UUID, account_id: UUID):
        account = await self.account_repo.get_by_id(account_id, user_id)
        if not account or not account.ativo:
            raise NotFoundError("Conta não encontrada", "ACCOUNT_NOT_FOUND")
        return account

    async def _validate_category(self, user_id: UUID, category_id: UUID, tipo: str):
        category = await self.cat_repo.get_by_id(category_id, user_id)
        if not category or not category.ativo:
            raise NotFoundError("Categoria não encontrada", "CATEGORY_NOT_FOUND")
        if category.tipo != tipo:
            raise BusinessRuleError(f"Categoria deve ser do tipo {tipo}", "INVALID_CATEGORY_TYPE")
        return category

    async def _next_date(self, freq: RecurrenceFrequency, dia_do_mes: int | None, dia_semana: int | None, current: date) -> date:
        if freq == RecurrenceFrequency.DIARIA:
            return current + timedelta(days=1)
        elif freq == RecurrenceFrequency.SEMANAL:
            return current + timedelta(weeks=1)
        elif freq == RecurrenceFrequency.MENSAL:
            if dia_do_mes:
                next_month = current.month + 1 if current.month < 12 else 1
                next_year = current.year + 1 if current.month == 12 else current.year
                try:
                    return date(next_year, next_month, min(dia_do_mes, 28))
                except ValueError:
                    return date(next_year, next_month, 28)
            return current + timedelta(days=30)
        elif freq == RecurrenceFrequency.ANUAL:
            try:
                return date(current.year + 1, current.month, current.day)
            except ValueError:
                return date(current.year + 1, current.month, 28)
        return current

    async def create(self, user_id: UUID, data: RecurrenceCreate) -> RecurringTransaction:
        await self._validate_account(user_id, data.conta_id)
        if data.categoria_id:
            await self._validate_category(user_id, data.categoria_id, data.tipo)

        proxima = data.data_inicio
        recurrence = RecurringTransaction(user_id=user_id, proxima_execucao=proxima, **data.model_dump())
        self.db.add(recurrence)
        await self.db.flush()
        await self.db.refresh(recurrence)
        return recurrence

    async def get(self, user_id: UUID, recurrence_id: UUID) -> RecurringTransaction:
        recurrence = await self.repo.get_by_id(recurrence_id, user_id)
        if not recurrence:
            raise NotFoundError("Recorrência não encontrada", "RECURRENCE_NOT_FOUND")
        return recurrence

    async def list(self, user_id: UUID, ativo_only: bool = True, page: int = 1, size: int = 20):
        recurrences = await self.repo.get_by_user(user_id, ativo_only, size, (page - 1) * size)
        total = await self.repo.count_by_user(user_id, ativo_only)
        return recurrences, total

    async def update(self, user_id: UUID, recurrence_id: UUID, data: RecurrenceUpdate) -> RecurringTransaction:
        recurrence = await self.get(user_id, recurrence_id)
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(recurrence, field, value)
        await self.db.flush()
        await self.db.refresh(recurrence)
        return recurrence

    async def delete(self, user_id: UUID, recurrence_id: UUID) -> None:
        recurrence = await self.get(user_id, recurrence_id)
        await self.repo.delete(recurrence)

    async def generate_pending(self, user_id: UUID, data_limite: date | None = None) -> RecurrenceGenerateResponse:
        if data_limite is None:
            data_limite = date.today()

        due = await self.repo.get_due_recurrences(user_id, data_limite)
        geradas = 0

        for rec in due:
            while rec.proxima_execucao <= data_limite:
                if rec.data_fim and rec.proxima_execucao > rec.data_fim:
                    break
                ocorrencia = rec.proxima_execucao
                occ_key = uuid5(NAMESPACE_URL, f"{rec.id}:{ocorrencia.isoformat()}")

                existing = await self.tx_repo.get_by_idempotency_key(user_id, occ_key)
                if not existing:
                    tx = Transaction(
                        user_id=user_id,
                        conta_id=rec.conta_id,
                        categoria_id=rec.categoria_id,
                        tipo=rec.tipo,
                        valor=rec.valor,
                        data=ocorrencia,
                        descricao=rec.descricao,
                        status=TransactionStatus.CONFIRMADO,
                        recorrencia_id=rec.id,
                        idempotency_key=occ_key,
                    )
                    self.db.add(tx)
                    geradas += 1

                rec.proxima_execucao = await self._next_date(rec.frequencia, rec.dia_do_mes, rec.dia_semana, rec.proxima_execucao)

            if rec.data_fim and rec.proxima_execucao > rec.data_fim:
                rec.ativo = False

        await self.db.flush()
        return RecurrenceGenerateResponse(geradas=geradas, message=f"{geradas} transações geradas")

    async def generate_by_id(self, user_id: UUID, recurrence_id: UUID, data_limite: date | None = None) -> RecurrenceGenerateResponse:
        rec = await self.get(user_id, recurrence_id)
        if not rec.ativo:
            raise BusinessRuleError("Recorrência inativa", "RECURRENCE_INACTIVE")

        if data_limite is None:
            data_limite = date.today()

        geradas = 0
        while rec.proxima_execucao <= data_limite:
            if rec.data_fim and rec.proxima_execucao > rec.data_fim:
                break
            ocorrencia = rec.proxima_execucao
            occ_key = uuid5(NAMESPACE_URL, f"{rec.id}:{ocorrencia.isoformat()}")

            existing = await self.tx_repo.get_by_idempotency_key(user_id, occ_key)
            if not existing:
                tx = Transaction(
                    user_id=user_id,
                    conta_id=rec.conta_id,
                    categoria_id=rec.categoria_id,
                    tipo=rec.tipo,
                    valor=rec.valor,
                    data=ocorrencia,
                    descricao=rec.descricao,
                    status=TransactionStatus.CONFIRMADO,
                    recorrencia_id=rec.id,
                    idempotency_key=occ_key,
                )
                self.db.add(tx)
                geradas += 1

            rec.proxima_execucao = await self._next_date(rec.frequencia, rec.dia_do_mes, rec.dia_semana, rec.proxima_execucao)

        if rec.data_fim and rec.proxima_execucao > rec.data_fim:
            rec.ativo = False

        await self.db.flush()
        return RecurrenceGenerateResponse(geradas=geradas, message=f"{geradas} transações geradas")