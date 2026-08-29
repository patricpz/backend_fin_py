from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional
from app.db.session import get_db
from app.core.deps import get_current_user, PaginationParams
from app.schemas.budget import BudgetCreate, BudgetUpdate, BudgetResponse, BudgetProgress
from app.services.budget_service import BudgetService
from app.schemas.common import Page
from app.models.user import User


router = APIRouter(prefix="/budgets", tags=["budgets"])


@router.post("", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
async def create_budget(data: BudgetCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = BudgetService(db)
    return await service.create(current_user.id, data)


@router.get("", response_model=Page[BudgetResponse])
async def list_budgets(
    mes: Optional[int] = None,
    ano: Optional[int] = None,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = BudgetService(db)
    budgets, total = await service.list(current_user.id, mes, ano, pagination.page, pagination.size)
    return Page.create(budgets, total, pagination.page, pagination.size)


@router.get("/{budget_id}", response_model=BudgetResponse)
async def get_budget(budget_id: UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = BudgetService(db)
    return await service.get(current_user.id, budget_id)


@router.get("/{budget_id}/progress", response_model=BudgetProgress)
async def get_budget_progress(budget_id: UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = BudgetService(db)
    return await service.get_progress(current_user.id, budget_id)


@router.patch("/{budget_id}", response_model=BudgetResponse)
async def update_budget(budget_id: UUID, data: BudgetUpdate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = BudgetService(db)
    return await service.update(current_user.id, budget_id, data)


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_budget(budget_id: UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = BudgetService(db)
    await service.delete(current_user.id, budget_id)