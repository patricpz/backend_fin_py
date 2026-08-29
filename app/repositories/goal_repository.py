from typing import Optional, Sequence
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base import BaseRepository
from app.models.goal import Goal, GoalContribution


class GoalRepository(BaseRepository[Goal]):
    def __init__(self, db: AsyncSession):
        super().__init__(Goal, db)

    async def get_by_user(self, user_id: UUID, status: Optional[str] = None, limit: int = 100, offset: int = 0) -> Sequence[Goal]:
        stmt = select(Goal).where(Goal.user_id == user_id)
        if status:
            stmt = stmt.where(Goal.status == status)
        stmt = stmt.order_by(Goal.criado_em.desc()).limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def count_by_user(self, user_id: UUID, status: Optional[str] = None) -> int:
        stmt = select(func.count()).select_from(Goal).where(Goal.user_id == user_id)
        if status:
            stmt = stmt.where(Goal.status == status)
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def get_by_id(self, id: UUID, user_id: UUID) -> Optional[Goal]:
        result = await self.db.execute(select(Goal).where(Goal.id == id, Goal.user_id == user_id))
        return result.scalar_one_or_none()


class GoalContributionRepository(BaseRepository[GoalContribution]):
    def __init__(self, db: AsyncSession):
        super().__init__(GoalContribution, db)

    async def get_by_goal(self, goal_id: UUID, limit: int = 100, offset: int = 0) -> Sequence[GoalContribution]:
        stmt = select(GoalContribution).where(GoalContribution.goal_id == goal_id).order_by(GoalContribution.data.desc()).limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_current_value(self, goal_id: UUID) -> float:
        from app.models.enums import GoalContributionType
        stmt = select(func.coalesce(func.sum(GoalContribution.valor), 0)).where(
            GoalContribution.goal_id == goal_id,
            GoalContribution.tipo == GoalContributionType.APORTE
        )
        result = await self.db.execute(stmt)
        aportes = result.scalar_one()

        stmt = select(func.coalesce(func.sum(GoalContribution.valor), 0)).where(
            GoalContribution.goal_id == goal_id,
            GoalContribution.tipo == GoalContributionType.RETIRADA
        )
        result = await self.db.execute(stmt)
        retiradas = result.scalar_one()

        return float(aportes) - float(retiradas)