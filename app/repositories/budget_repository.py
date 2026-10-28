from typing import Optional, Sequence
from uuid import UUID
from datetime import date
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base import BaseRepository
from app.models.budget import Budget


class BudgetRepository(BaseRepository[Budget]):
    def __init__(self, db: AsyncSession):
        super().__init__(Budget, db)

    async def get_by_user(self, user_id: UUID, mes: Optional[int] = None, ano: Optional[int] = None, limit: int = 100, offset: int = 0) -> Sequence[Budget]:
        stmt = select(Budget).options(selectinload(Budget.category)).where(Budget.user_id == user_id)
        if mes:
            stmt = stmt.where(Budget.mes == mes)
        if ano:
            stmt = stmt.where(Budget.ano == ano)
        stmt = stmt.order_by(Budget.ano.desc(), Budget.mes.desc()).limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def count_by_user(self, user_id: UUID, mes: Optional[int] = None, ano: Optional[int] = None) -> int:
        stmt = select(func.count()).select_from(Budget).where(Budget.user_id == user_id)
        if mes:
            stmt = stmt.where(Budget.mes == mes)
        if ano:
            stmt = stmt.where(Budget.ano == ano)
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def get_by_id(self, id: UUID, user_id: UUID) -> Optional[Budget]:
        result = await self.db.execute(
            select(Budget).options(selectinload(Budget.category)).where(Budget.id == id, Budget.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_categoria_periodo(self, user_id: UUID, categoria_id: UUID, mes: int, ano: int) -> Optional[Budget]:
        result = await self.db.execute(
            select(Budget).options(selectinload(Budget.category)).where(
                Budget.user_id == user_id,
                Budget.categoria_id == categoria_id,
                Budget.mes == mes,
                Budget.ano == ano
            )
        )
        return result.scalar_one_or_none()
