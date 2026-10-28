from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional
from app.db.session import get_db
from app.core.deps import get_current_user, PaginationParams
from app.schemas.goal import GoalCreate, GoalUpdate, GoalResponse, GoalProgressResponse, GoalContributionCreate, GoalContributionResponse
from app.services.goal_service import GoalService
from app.schemas.common import Page
from app.models.user import User


router = APIRouter(prefix="/goals", tags=["goals"])


@router.post("", response_model=GoalResponse, status_code=status.HTTP_201_CREATED)
async def create_goal(data: GoalCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = GoalService(db)
    return await service.create(current_user.id, data)


@router.get("", response_model=Page[GoalResponse])
async def list_goals(
    status: Optional[str] = None,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = GoalService(db)
    goals, total = await service.list(current_user.id, status, pagination.page, pagination.size)
    return Page.create(goals, total, pagination.page, pagination.size)


@router.get("/{goal_id}", response_model=GoalResponse)
async def get_goal(goal_id: UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = GoalService(db)
    return await service.get(current_user.id, goal_id)


@router.get("/{goal_id}/progress", response_model=GoalProgressResponse)
async def get_goal_progress(goal_id: UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = GoalService(db)
    return await service.get_progress(current_user.id, goal_id)


@router.post("/{goal_id}/contributions", response_model=GoalContributionResponse, status_code=status.HTTP_201_CREATED)
async def add_contribution(goal_id: UUID, data: GoalContributionCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = GoalService(db)
    return await service.add_contribution(current_user.id, goal_id, data)


@router.get("/{goal_id}/contributions", response_model=Page[GoalContributionResponse])
async def list_contributions(
    goal_id: UUID,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = GoalService(db)
    contributions, total = await service.get_contributions(current_user.id, goal_id, pagination.page, pagination.size)
    return Page.create(contributions, total, pagination.page, pagination.size)


@router.patch("/{goal_id}", response_model=GoalResponse)
async def update_goal(goal_id: UUID, data: GoalUpdate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = GoalService(db)
    return await service.update(current_user.id, goal_id, data)


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_goal(goal_id: UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = GoalService(db)
    await service.delete(current_user.id, goal_id)
