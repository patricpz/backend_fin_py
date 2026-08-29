from typing import Optional, Sequence
from uuid import UUID
from datetime import date
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base import BaseRepository
from app.models.recurrence import RecurringTransaction


class RecurrenceRepository(BaseRepository[RecurringTransaction]):
    def __init__(self, db: AsyncSession):
        super().__init__(RecurringTransaction, db)

    async def get_by_user(self, user_id: UUID, ativo_only: bool = True, limit: int = 100, offset: int = 0) -> Sequence[RecurringTransaction]:
        stmt = select(RecurringTransaction).where(RecurringTransaction.user_id == user_id)
        if ativo_only:
            stmt = stmt.where(RecurringTransaction.ativo == True)
        stmt = stmt.order_by(RecurringTransaction.proxima_execucao).limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def count_by_user(self, user_id: UUID, ativo_only: bool = True) -> int:
        stmt = select(func.count()).select_from(RecurringTransaction).where(RecurringTransaction.user_id == user_id)
        if ativo_only:
            stmt = stmt.where(RecurringTransaction.ativo == True)
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def get_by_id(self, id: UUID, user_id: UUID) -> Optional[RecurringTransaction]:
        result = await self.db.execute(select(RecurringTransaction).where(RecurringTransaction.id == id, RecurringTransaction.user_id == user_id))
        return result.scalar_one_or_none()

    async def get_due_recurrences(self, user_id: UUID, data_limite: date) -> Sequence[RecurringTransaction]:
        stmt = select(RecurringTransaction).where(
            RecurringTransaction.user_id == user_id,
            RecurringTransaction.ativo == True,
            RecurringTransaction.proxima_execucao <= data_limite,
            RecurringTransaction.data_inicio <= data_limite,
            (RecurringTransaction.data_fim.is_(None) | (RecurringTransaction.data_fim >= data_limite))
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()