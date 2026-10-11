from __future__ import annotations

from uuid import UUID
from datetime import date
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.goal import Goal, GoalContribution
from app.repositories.goal_repository import GoalRepository, GoalContributionRepository
from app.schemas.goal import GoalCreate, GoalUpdate, GoalResponse, GoalContributionCreate, GoalContributionResponse
from app.core.exceptions import NotFoundError, BusinessRuleError
from app.models.enums import GoalStatus, GoalContributionType


class GoalService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = GoalRepository(db)
        self.contrib_repo = GoalContributionRepository(db)

    async def _with_progress(self, goal: Goal) -> Goal:
        current = await self.contrib_repo.get_current_value(goal.id)
        goal.valor_atual = Decimal(str(current)).quantize(Decimal("0.01"))
        percentual = min((current / float(goal.valor_alvo)) * 100, 100) if goal.valor_alvo > 0 else 0
        goal.progresso_percentual = percentual
        return goal

    async def create(self, user_id: UUID, data: GoalCreate) -> Goal:
        goal = Goal(user_id=user_id, **data.model_dump())
        self.db.add(goal)
        await self.db.flush()
        await self.db.refresh(goal)
        goal.valor_atual = Decimal("0.00")
        goal.progresso_percentual = 0.0
        return goal

    async def get(self, user_id: UUID, goal_id: UUID) -> Goal:
        goal = await self.repo.get_by_id(goal_id, user_id)
        if not goal:
            raise NotFoundError("Meta não encontrada", "GOAL_NOT_FOUND")
        return await self._with_progress(goal)

    async def list(self, user_id: UUID, status: str | None = None, page: int = 1, size: int = 20):
        goals = await self.repo.get_by_user(user_id, status, size, (page - 1) * size)
        total = await self.repo.count_by_user(user_id, status)
        goals = [await self._with_progress(g) for g in goals]
        return goals, total

    async def update(self, user_id: UUID, goal_id: UUID, data: GoalUpdate) -> Goal:
        goal = await self.repo.get_by_id(goal_id, user_id)
        if not goal:
            raise NotFoundError("Meta não encontrada", "GOAL_NOT_FOUND")
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(goal, field, value)
        await self.db.flush()
        await self.db.refresh(goal)
        return await self._with_progress(goal)

    async def delete(self, user_id: UUID, goal_id: UUID) -> None:
        goal = await self.get(user_id, goal_id)
        await self.repo.delete(goal)

    async def add_contribution(self, user_id: UUID, goal_id: UUID, data: GoalContributionCreate) -> GoalContribution:
        goal = await self.get(user_id, goal_id)
        if goal.status == GoalStatus.CONCLUIDA:
            raise BusinessRuleError("Meta já concluída", "GOAL_COMPLETED")
        if goal.status == GoalStatus.CANCELADA:
            raise BusinessRuleError("Meta cancelada", "GOAL_CANCELLED")

        contribution = GoalContribution(goal_id=goal_id, **data.model_dump())
        self.db.add(contribution)
        await self.db.flush()
        await self.db.refresh(contribution)

        current = await self.contrib_repo.get_current_value(goal_id)
        if current >= float(goal.valor_alvo):
            goal.status = GoalStatus.CONCLUIDA
            await self.db.flush()
        return contribution

    async def get_contributions(self, user_id: UUID, goal_id: UUID, page: int = 1, size: int = 20):
        await self.get(user_id, goal_id)
        contributions = await self.contrib_repo.get_by_goal(goal_id, size, (page - 1) * size)
        return contributions

    async def get_progress(self, user_id: UUID, goal_id: UUID) -> dict:
        goal = await self.get(user_id, goal_id)
        current = await self.contrib_repo.get_current_value(goal_id)
        percentual = min((current / float(goal.valor_alvo)) * 100, 100) if goal.valor_alvo > 0 else 0
        return {
            "goal_id": goal.id,
            "valor_alvo": goal.valor_alvo,
            "valor_atual": Decimal(str(current)).quantize(Decimal("0.01")),
            "progresso_percentual": percentual,
            "status": goal.status,
        }