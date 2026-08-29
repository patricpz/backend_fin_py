from typing import Optional, Sequence
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base import BaseRepository
from app.models.account import Account


class AccountRepository(BaseRepository[Account]):
    def __init__(self, db: AsyncSession):
        super().__init__(Account, db)

    async def get_by_user(self, user_id: UUID, ativo_only: bool = True, limit: int = 100, offset: int = 0) -> Sequence[Account]:
        stmt = select(Account).where(Account.user_id == user_id)
        if ativo_only:
            stmt = stmt.where(Account.ativo == True)
        stmt = stmt.order_by(Account.criado_em.desc()).limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def count_by_user(self, user_id: UUID, ativo_only: bool = True) -> int:
        stmt = select(func.count()).select_from(Account).where(Account.user_id == user_id)
        if ativo_only:
            stmt = stmt.where(Account.ativo == True)
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def get_by_id(self, id: UUID, user_id: UUID) -> Optional[Account]:
        result = await self.db.execute(select(Account).where(Account.id == id, Account.user_id == user_id))
        return result.scalar_one_or_none()

    async def has_transactions(self, account_id: UUID) -> bool:
        from app.models.transaction import Transaction
        result = await self.db.execute(
            select(func.count()).select_from(Transaction).where(Transaction.conta_id == account_id)
        )
        return result.scalar_one() > 0