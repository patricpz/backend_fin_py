from typing import Optional, Sequence, List
from uuid import UUID
from datetime import date
from decimal import Decimal
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base import BaseRepository
from app.models.transaction import Transaction
from app.models.enums import TransactionType, TransactionStatus
from app.schemas.transaction import TransactionFilters


class TransactionRepository(BaseRepository[Transaction]):
    def __init__(self, db: AsyncSession):
        super().__init__(Transaction, db)

    async def get_by_user(
        self,
        user_id: UUID,
        filters: Optional[TransactionFilters] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Sequence[Transaction]:
        stmt = select(Transaction).where(Transaction.user_id == user_id)

        if filters:
            if filters.conta_id:
                stmt = stmt.where(Transaction.conta_id == filters.conta_id)
            if filters.categoria_id:
                stmt = stmt.where(Transaction.categoria_id == filters.categoria_id)
            if filters.tipo:
                stmt = stmt.where(Transaction.tipo == filters.tipo)
            if filters.status:
                stmt = stmt.where(Transaction.status == filters.status)
            if filters.data_inicio:
                stmt = stmt.where(Transaction.data >= filters.data_inicio)
            if filters.data_fim:
                stmt = stmt.where(Transaction.data <= filters.data_fim)
            if filters.descricao:
                stmt = stmt.where(Transaction.descricao.ilike(f"%{filters.descricao}%"))

        stmt = stmt.order_by(Transaction.data.desc(), Transaction.criado_em.desc()).limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def count_by_user(self, user_id: UUID, filters: Optional[TransactionFilters] = None) -> int:
        stmt = select(func.count()).select_from(Transaction).where(Transaction.user_id == user_id)

        if filters:
            if filters.conta_id:
                stmt = stmt.where(Transaction.conta_id == filters.conta_id)
            if filters.categoria_id:
                stmt = stmt.where(Transaction.categoria_id == filters.categoria_id)
            if filters.tipo:
                stmt = stmt.where(Transaction.tipo == filters.tipo)
            if filters.status:
                stmt = stmt.where(Transaction.status == filters.status)
            if filters.data_inicio:
                stmt = stmt.where(Transaction.data >= filters.data_inicio)
            if filters.data_fim:
                stmt = stmt.where(Transaction.data <= filters.data_fim)
            if filters.descricao:
                stmt = stmt.where(Transaction.descricao.ilike(f"%{filters.descricao}%"))

        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def get_by_id(self, id: UUID, user_id: UUID) -> Optional[Transaction]:
        result = await self.db.execute(select(Transaction).where(Transaction.id == id, Transaction.user_id == user_id))
        return result.scalar_one_or_none()

    async def get_by_idempotency_key(self, user_id: UUID, key: UUID) -> Optional[Transaction]:
        result = await self.db.execute(
            select(Transaction).where(Transaction.user_id == user_id, Transaction.idempotency_key == key)
        )
        return result.scalar_one_or_none()

    async def get_account_balance(self, account_id: UUID) -> Decimal:
        stmt = select(func.coalesce(func.sum(Transaction.valor), 0)).where(
            Transaction.conta_id == account_id,
            Transaction.status == TransactionStatus.CONFIRMADO,
            or_(
                Transaction.tipo == TransactionType.RECEITA,
                Transaction.tipo == TransactionType.DESPESA,
            )
        )
        result = await self.db.execute(stmt)
        receitas = result.scalar_one()

        stmt = select(func.coalesce(func.sum(Transaction.valor), 0)).where(
            Transaction.conta_id == account_id,
            Transaction.status == TransactionStatus.CONFIRMADO,
            Transaction.tipo == TransactionType.TRANSFERENCIA
        )
        result = await self.db.execute(stmt)
        transferencias_enviadas = result.scalar_one()

        stmt = select(func.coalesce(func.sum(Transaction.valor), 0)).where(
            Transaction.conta_destino_id == account_id,
            Transaction.status == TransactionStatus.CONFIRMADO,
            Transaction.tipo == TransactionType.TRANSFERENCIA
        )
        result = await self.db.execute(stmt)
        transferencias_recebidas = result.scalar_one()

        return Decimal(str(receitas)) - Decimal(str(transferencias_enviadas)) + Decimal(str(transferencias_recebidas))

    async def get_category_spending(self, user_id: UUID, categoria_id: UUID, data_inicio: date, data_fim: date) -> Decimal:
        from app.models.category import Category
        stmt = select(func.coalesce(func.sum(Transaction.valor), 0)).where(
            Transaction.user_id == user_id,
            Transaction.status == TransactionStatus.CONFIRMADO,
            Transaction.tipo == TransactionType.DESPESA,
            Transaction.data >= data_inicio,
            Transaction.data <= data_fim,
            Transaction.categoria_id == categoria_id
        )
        result = await self.db.execute(stmt)
        return Decimal(str(result.scalar_one()))