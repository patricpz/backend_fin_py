from typing import Optional, Sequence
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base import BaseRepository
from app.models.category import Category


class CategoryRepository(BaseRepository[Category]):
    def __init__(self, db: AsyncSession):
        super().__init__(Category, db)

    async def get_by_user(self, user_id: UUID, tipo: Optional[str] = None, ativo_only: bool = True, limit: int = 100, offset: int = 0) -> Sequence[Category]:
        stmt = select(Category).where(Category.user_id == user_id)
        if tipo:
            stmt = stmt.where(Category.tipo == tipo)
        if ativo_only:
            stmt = stmt.where(Category.ativo == True)
        stmt = stmt.order_by(Category.nome).limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def count_by_user(self, user_id: UUID, tipo: Optional[str] = None, ativo_only: bool = True) -> int:
        stmt = select(func.count()).select_from(Category).where(Category.user_id == user_id)
        if tipo:
            stmt = stmt.where(Category.tipo == tipo)
        if ativo_only:
            stmt = stmt.where(Category.ativo == True)
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def get_by_id(self, id: UUID, user_id: UUID) -> Optional[Category]:
        result = await self.db.execute(select(Category).where(Category.id == id, Category.user_id == user_id))
        return result.scalar_one_or_none()

    async def get_tree(self, user_id: UUID, tipo: Optional[str] = None) -> Sequence[Category]:
        stmt = select(Category).where(Category.user_id == user_id, Category.categoria_pai_id.is_(None))
        if tipo:
            stmt = stmt.where(Category.tipo == tipo)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_children(self, user_id: UUID, categoria_pai_id: UUID, ativo_only: bool = True) -> Sequence[Category]:
        stmt = select(Category).where(
            Category.user_id == user_id,
            Category.categoria_pai_id == categoria_pai_id,
        )
        if ativo_only:
            stmt = stmt.where(Category.ativo == True)
        stmt = stmt.order_by(Category.nome)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def has_children(self, category_id: UUID) -> bool:
        result = await self.db.execute(select(func.count()).select_from(Category).where(Category.categoria_pai_id == category_id))
        return result.scalar_one() > 0

    async def has_transactions_or_budgets(self, category_id: UUID) -> bool:
        from app.models.transaction import Transaction
        from app.models.budget import Budget
        t_count = await self.db.execute(select(func.count()).select_from(Transaction).where(Transaction.categoria_id == category_id))
        b_count = await self.db.execute(select(func.count()).select_from(Budget).where(Budget.categoria_id == category_id))
        return t_count.scalar_one() > 0 or b_count.scalar_one() > 0