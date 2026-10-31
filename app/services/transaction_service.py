from __future__ import annotations

import calendar
from uuid import UUID
from datetime import date, timedelta
from decimal import Decimal, ROUND_FLOOR
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.models.transaction import Transaction
from app.models.account import Account
from app.models.category import Category
from app.models.installment import Installment
from app.repositories.transaction_repository import TransactionRepository
from app.repositories.account_repository import AccountRepository
from app.repositories.category_repository import CategoryRepository
from app.schemas.transaction import (
    TransactionCreate,
    TransactionUpdate,
    TransactionFilters,
    InstallmentPayRequest,
    TransactionInstallmentResponse,
    InstallmentsSummaryResponse,
)
from app.schemas.installment import InstallmentCreate
from app.core.exceptions import NotFoundError, ConflictError, BusinessRuleError
from app.models.enums import TransactionType, TransactionStatus


class TransactionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.tx_repo = TransactionRepository(db)
        self.account_repo = AccountRepository(db)
        self.category_repo = CategoryRepository(db)

    async def _validate_account(self, user_id: UUID, account_id: UUID) -> Account:
        account = await self.account_repo.get_by_id(account_id, user_id)
        if not account:
            raise NotFoundError("Conta não encontrada", "ACCOUNT_NOT_FOUND")
        if not account.ativo:
            raise BusinessRuleError("Conta inativa", "ACCOUNT_INACTIVE")
        return account

    async def _validate_category(self, user_id: UUID, category_id: UUID, expected_tipo: str | None = None) -> Category:
        category = await self.category_repo.get_by_id(category_id, user_id)
        if not category:
            raise NotFoundError("Categoria não encontrada", "CATEGORY_NOT_FOUND")
        if not category.ativo:
            raise BusinessRuleError("Categoria inativa", "CATEGORY_INACTIVE")
        if expected_tipo and category.tipo != expected_tipo:
            raise BusinessRuleError(f"Categoria deve ser do tipo {expected_tipo}", "INVALID_CATEGORY_TYPE")
        return category

    async def _validate_transfer(self, user_id: UUID, conta_id: UUID, conta_destino_id: UUID) -> tuple[Account, Account]:
        if conta_id == conta_destino_id:
            raise BusinessRuleError("Conta de origem e destino devem ser diferentes", "SAME_ACCOUNT_TRANSFER")
        conta_origem = await self._validate_account(user_id, conta_id)
        conta_destino = await self._validate_account(user_id, conta_destino_id)
        return conta_origem, conta_destino

    async def create(self, user_id: UUID, data: TransactionCreate) -> Transaction:
        if data.idempotency_key:
            existing = await self.tx_repo.get_by_idempotency_key(user_id, data.idempotency_key)
            if existing:
                return existing

        # Validações específicas para despesa parcelada
        if data.is_installment:
            if data.installment_count is None or data.installment_count < 2:
                raise BusinessRuleError(
                    "installment_count deve ser >= 2 para despesas parceladas",
                    "INSTALLMENT_COUNT_INVALID"
                )
            if data.tipo != TransactionType.DESPESA:
                raise BusinessRuleError(
                    "Despesas parceladas só são permitidas para tipo 'despesa'",
                    "INSTALLMENT_ONLY_DESPESA"
                )
            if data.first_due_date is None:
                raise BusinessRuleError(
                    "first_due_date é obrigatório para despesas parceladas",
                    "FIRST_DUE_DATE_REQUIRED"
                )
            if data.paid_installments < 0:
                raise BusinessRuleError(
                    "paid_installments não pode ser negativo",
                    "INVALID_PAID_INSTALLMENTS"
                )
            if data.installment_count is not None and data.paid_installments > data.installment_count:
                raise BusinessRuleError(
                    "paid_installments não pode exceder installment_count",
                    "PAID_EXCEEDS_COUNT"
                )

        if data.tipo == TransactionType.TRANSFERENCIA:
            await self._validate_transfer(user_id, data.conta_id, data.conta_destino_id)
            if data.categoria_id:
                raise BusinessRuleError("Transferências não devem ter categoria", "TRANSFER_NO_CATEGORY")
        elif data.tipo == TransactionType.RECEITA:
            await self._validate_account(user_id, data.conta_id)
            await self._validate_category(user_id, data.categoria_id, TransactionType.RECEITA)
        elif data.tipo == TransactionType.DESPESA:
            await self._validate_account(user_id, data.conta_id)
            await self._validate_category(user_id, data.categoria_id, TransactionType.DESPESA)

        transaction = Transaction(user_id=user_id, **data.model_dump())
        self.db.add(transaction)
        await self.db.flush()
        await self.db.refresh(transaction)
        return transaction

    async def get(self, user_id: UUID, transaction_id: UUID) -> Transaction:
        transaction = await self.tx_repo.get_by_id(transaction_id, user_id)
        if not transaction:
            raise NotFoundError("Transação não encontrada", "TRANSACTION_NOT_FOUND")
        return transaction

    async def list(self, user_id: UUID, filters: TransactionFilters | None, page: int = 1, size: int = 20):
        transactions = await self.tx_repo.get_by_user(user_id, filters, size, (page - 1) * size)
        total = await self.tx_repo.count_by_user(user_id, filters)
        return transactions, total

    async def update(self, user_id: UUID, transaction_id: UUID, data: TransactionUpdate) -> Transaction:
        transaction = await self.get(user_id, transaction_id)
        update_data = data.model_dump(exclude_unset=True)

        if "tipo" in update_data or "conta_id" in update_data or "conta_destino_id" in update_data or "categoria_id" in update_data:
            tipo = update_data.get("tipo", transaction.tipo)
            conta_id = update_data.get("conta_id", transaction.conta_id)
            conta_destino_id = update_data.get("conta_destino_id", transaction.conta_destino_id)
            categoria_id = update_data.get("categoria_id", transaction.categoria_id)

            if tipo == TransactionType.TRANSFERENCIA:
                await self._validate_transfer(user_id, conta_id, conta_destino_id)
                if categoria_id:
                    raise BusinessRuleError("Transferências não devem ter categoria", "TRANSFER_NO_CATEGORY")
            elif tipo == TransactionType.RECEITA:
                await self._validate_account(user_id, conta_id)
                await self._validate_category(user_id, categoria_id, TransactionType.RECEITA)
            elif tipo == TransactionType.DESPESA:
                await self._validate_account(user_id, conta_id)
                await self._validate_category(user_id, categoria_id, TransactionType.DESPESA)

        # Validação de campos de parcelamento no update
        new_is_installment = update_data.get("is_installment", transaction.is_installment)
        if new_is_installment:
            new_count = update_data.get("installment_count", transaction.installment_count)
            new_paid = update_data.get("paid_installments", transaction.paid_installments)
            new_first_due = update_data.get("first_due_date", transaction.first_due_date)
            new_tipo = update_data.get("tipo", transaction.tipo)

            if new_tipo != TransactionType.DESPESA:
                raise BusinessRuleError(
                    "Despesas parceladas só são permitidas para tipo 'despesa'",
                    "INSTALLMENT_ONLY_DESPESA"
                )
            if new_count is None or new_count < 2:
                raise BusinessRuleError(
                    "installment_count deve ser >= 2 para despesas parceladas",
                    "INSTALLMENT_COUNT_INVALID"
                )
            if new_first_due is None:
                raise BusinessRuleError(
                    "first_due_date é obrigatório para despesas parceladas",
                    "FIRST_DUE_DATE_REQUIRED"
                )
            if new_paid < 0:
                raise BusinessRuleError(
                    "paid_installments não pode ser negativo",
                    "INVALID_PAID_INSTALLMENTS"
                )
            if new_paid > new_count:
                raise BusinessRuleError(
                    "paid_installments não pode exceder installment_count",
                    "PAID_EXCEEDS_COUNT"
                )

        for field, value in update_data.items():
            setattr(transaction, field, value)

        await self.db.flush()
        await self.db.refresh(transaction)
        if transaction.is_installment:
            self._attach_progress(transaction)
        return transaction

    async def delete(self, user_id: UUID, transaction_id: UUID) -> None:
        transaction = await self.get(user_id, transaction_id)
        await self.tx_repo.delete(transaction)

    async def confirm(self, user_id: UUID, transaction_id: UUID) -> Transaction:
        transaction = await self.get(user_id, transaction_id)
        if transaction.status == TransactionStatus.CONFIRMADO:
            return transaction
        transaction.status = TransactionStatus.CONFIRMADO
        await self.db.flush()
        await self.db.refresh(transaction)
        return transaction

    async def parcelar(self, user_id: UUID, transaction_id: UUID, data: InstallmentCreate) -> Transaction:
        """Cria parcelas para uma transação de despesa ou receita."""
        transaction = await self.tx_repo.get_by_id_with_installments(transaction_id, user_id)
        if not transaction:
            raise NotFoundError("Transação não encontrada", "TRANSACTION_NOT_FOUND")

        # Só despesas e receitas podem ser parceladas
        if transaction.tipo not in (TransactionType.DESPESA, TransactionType.RECEITA):
            raise BusinessRuleError(
                "Apenas despesas e receitas podem ser parceladas",
                "CANNOT_PARCELIZE_TRANSFER"
            )

        # Se já tem parcelas, impede nova parcelação
        if transaction.installments and len(transaction.installments) > 0:
            raise BusinessRuleError(
                "Transação já possui parcelas",
                "ALREADY_INSTALLMENTED"
            )

        valor_total = Decimal(str(transaction.valor))
        numero_parcelas = data.numero_parcelas

        # Se valor_por_parcela não informado, divide igualmente
        if data.valor_por_parcela:
            valor_por_parcela = data.valor_por_parcela
            total_parcelas = valor_por_parcela * numero_parcelas
            if total_parcelas > valor_total:
                raise BusinessRuleError(
                    "O valor total das parcelas não pode exceder o valor da transação",
                    "INSTALLMENT_TOTAL_EXCEEDED"
                )
        else:
            # Divisão inteira; o resto permanece na transação mãe
            valor_por_parcela = valor_total / numero_parcelas

        data_atual = date.today()
        data_inicio = data.data_inicio if data.data_inicio >= data_atual else data_atual

        installments = []
        for i in range(numero_parcelas):
            vencimento = data_inicio + timedelta(days=30 * i)
            installment = Installment(
                transaction_id=transaction_id,
                parcela_numero=i + 1,
                valor=float(valor_por_parcela.quantize(Decimal("0.01"))),
                data_vencimento=vencimento,
                status=TransactionStatus.CONFIRMADO,
            )
            installments.append(installment)
            self.db.add(installment)

        # Atualiza a transação para refletir o número de parcelas
        transaction.installments_total_count = numero_parcelas
        if transaction.status == TransactionStatus.PENDENTE:
            transaction.status = TransactionStatus.CONFIRMADO

        await self.db.flush()
        await self.db.refresh(transaction)
        return transaction

    async def get_installments(self, user_id: UUID, transaction_id: UUID) -> list[Installment]:
        transaction = await self.tx_repo.get_by_id_with_installments(transaction_id, user_id)
        if not transaction:
            raise NotFoundError("Transação não encontrada", "TRANSACTION_NOT_FOUND")
        return list(transaction.installments) if transaction.installments else []

    # --- Installment (parcelada) business logic helpers ---

    @staticmethod
    def _add_months(d: date, months: int) -> date:
        """Soma meses a uma data, ajustando dia se necessário (ex.: 31/01 + 1m -> 28/02)."""
        y = d.year + (d.month - 1 + months) // 12
        m = (d.month - 1 + months) % 12 + 1
        day = min(d.day, calendar.monthrange(y, m)[1])
        return date(y, m, day)

    @staticmethod
    def _calculate_installment_progress(tx: Transaction) -> dict:
        """Calcula campos derivados de progresso de pagamento para uma transação parcelada.

        Returns dict com: installment_amount, remaining_installments, progress_percent,
        paid_amount, remaining_amount, next_due_date, is_completed, installment_display, progress_display.
        """
        if not tx.is_installment or not tx.installment_count:
            return {
                "installment_amount": None,
                "remaining_installments": None,
                "progress_percent": None,
                "paid_amount": None,
                "remaining_amount": None,
                "next_due_date": None,
                "is_completed": False,
                "installment_display": None,
                "progress_display": None,
            }

        total = Decimal(str(tx.valor))
        count = tx.installment_count
        paid = tx.paid_installments

        # installmentAmount = floor(total / count, 2 casas); diferença na última
        installment_amount = (total / count).quantize(Decimal("0.01"), rounding=ROUND_FLOOR)
        # paidAmount = soma das parcelas pagas (floor para parcelas completas, última pode diferir)
        if paid >= count:
            paid_amount = total
        else:
            paid_amount = (installment_amount * paid).quantize(Decimal("0.01"))

        remaining_amount = (total - paid_amount).quantize(Decimal("0.01"))
        remaining_installments = max(0, count - paid)
        progress_percent = round((paid / count) * 100) if count else 0
        is_completed = paid >= count

        next_due_date = None
        if not is_completed and tx.first_due_date:
            next_due_date = TransactionService._add_months(tx.first_due_date, paid)

        installment_display = f"{paid}/{count}" if count else None
        progress_display = f"{progress_percent}%" if progress_percent is not None else None

        return {
            "installment_amount": installment_amount,
            "remaining_installments": remaining_installments,
            "progress_percent": progress_percent,
            "paid_amount": paid_amount,
            "remaining_amount": remaining_amount,
            "next_due_date": next_due_date,
            "is_completed": is_completed,
            "installment_display": installment_display,
            "progress_display": progress_display,
        }

    def _attach_progress(self, tx: Transaction) -> Transaction:
        """Anexa campos calculados ao objeto Transaction (transiente)."""
        prog = self._calculate_installment_progress(tx)
        for k, v in prog.items():
            setattr(tx, k, v)
        return tx

    async def list_installments(self, user_id: UUID, filters: TransactionFilters | None, page: int = 1, size: int = 20):
        """Lista apenas despesas parceladas do usuário com progresso calculado."""
        # Força filtro is_installment=True
        if filters is None:
            filters = TransactionFilters()
        filters.is_installment = True

        transactions = await self.tx_repo.get_by_user(user_id, filters, size, (page - 1) * size)
        total = await self.tx_repo.count_by_user(user_id, filters)

        for tx in transactions:
            self._attach_progress(tx)
        return transactions, total

    async def pay_installment(
        self,
        user_id: UUID,
        transaction_id: UUID,
        payload: InstallmentPayRequest | None = None
    ) -> Transaction:
        """Registra pagamento de uma parcela (incrementa paid_installments em 1 por padrão).

        Aceita `paid_installments` no payload para correção manual (ex.: 3 de 10).
        Se payload omitido ou paid_installments for None, incrementa em 1.
        Validações:
        - 404 se não existe ou não pertence ao usuário.
        - 409 se já concluída (paid >= count).
        - 400 se paid_installments fora do intervalo [0, count].
        """
        transaction = await self.tx_repo.get_by_id(transaction_id, user_id)
        if not transaction:
            raise NotFoundError("Transação não encontrada", "TRANSACTION_NOT_FOUND")

        if not transaction.is_installment:
            raise BusinessRuleError("Transação não é uma despesa parcelada", "NOT_INSTALLMENT_TRANSACTION")

        count = transaction.installment_count
        if count is None or count < 2:
            raise BusinessRuleError("Transação parcelada inválida (installment_count)", "INVALID_INSTALLMENT_COUNT")

        if transaction.paid_installments >= count:
            raise ConflictError(
                "Despesa parcelada já está concluída; não é possível registrar mais pagamentos",
                "INSTALLMENT_ALREADY_COMPLETED"
            )

        if payload is not None and payload.paid_installments is not None:
            new_paid = payload.paid_installments
        else:
            new_paid = transaction.paid_installments + 1

        if new_paid < 0 or new_paid > count:
            raise BusinessRuleError(
                f"paid_installments deve estar entre 0 e {count}",
                "INVALID_PAID_INSTALLMENTS"
            )

        transaction.paid_installments = new_paid
        await self.db.flush()
        await self.db.refresh(transaction)
        return transaction

    async def get_installments_summary(
        self,
        user_id: UUID,
        filters: TransactionFilters | None = None
    ) -> InstallmentsSummaryResponse:
        """Calcula métricas consolidadas dos parcelamentos do usuário."""
        if filters is None:
            filters = TransactionFilters()
        filters.is_installment = True

        transactions = await self.tx_repo.get_all_by_user(user_id, filters)

        total_despesas_parceladas = len(transactions)
        ativas_count = 0
        concluidas_count = 0
        valor_total_original = Decimal("0.00")
        valor_total_pago = Decimal("0.00")
        valor_total_restante = Decimal("0.00")
        total_parcelas = 0
        total_parcelas_pagas = 0
        total_parcelas_restantes = 0
        next_due_dates = []

        for tx in transactions:
            prog = self._calculate_installment_progress(tx)
            valor_total_original += Decimal(str(tx.valor))
            if prog["is_completed"]:
                concluidas_count += 1
            else:
                ativas_count += 1
                if prog["next_due_date"]:
                    next_due_dates.append(prog["next_due_date"])

            if prog["paid_amount"]:
                valor_total_pago += prog["paid_amount"]
            if prog["remaining_amount"]:
                valor_total_restante += prog["remaining_amount"]
            if tx.installment_count:
                total_parcelas += tx.installment_count
            total_parcelas_pagas += tx.paid_installments
            if prog["remaining_installments"]:
                total_parcelas_restantes += prog["remaining_installments"]

        proximo_vencimento = min(next_due_dates) if next_due_dates else None
        percentual_geral = (
            round((valor_total_pago / valor_total_original) * 100)
            if valor_total_original > 0
            else 0
        )

        return InstallmentsSummaryResponse(
            total_despesas_parceladas=total_despesas_parceladas,
            ativas_count=ativas_count,
            concluidas_count=concluidas_count,
            valor_total_original=valor_total_original.quantize(Decimal("0.01")),
            valor_total_pago=valor_total_pago.quantize(Decimal("0.01")),
            valor_total_restante=valor_total_restante.quantize(Decimal("0.01")),
            total_parcelas=total_parcelas,
            total_parcelas_pagas=total_parcelas_pagas,
            total_parcelas_restantes=total_parcelas_restantes,
            percentual_geral_pago=percentual_geral,
            proximo_vencimento=proximo_vencimento,
        )