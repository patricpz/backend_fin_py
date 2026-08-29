from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional
from app.db.session import get_db
from app.core.deps import get_current_user
from app.schemas.report import MonthlySummary, CategorySpendingReport, BalanceEvolutionReport, BudgetVsActualReport
from app.services.report_service import ReportService
from app.models.user import User


router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/monthly-summary", response_model=MonthlySummary)
async def get_monthly_summary(
    mes: int,
    ano: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = ReportService(db)
    return await service.monthly_summary(current_user.id, mes, ano)


@router.get("/category-spending", response_model=CategorySpendingReport)
async def get_category_spending(
    mes: int,
    ano: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = ReportService(db)
    return await service.category_spending(current_user.id, mes, ano)


@router.get("/balance-evolution", response_model=BalanceEvolutionReport)
async def get_balance_evolution(
    conta_id: UUID,
    mes: int,
    ano: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = ReportService(db)
    return await service.balance_evolution(current_user.id, conta_id, mes, ano)


@router.get("/budget-vs-actual", response_model=BudgetVsActualReport)
async def get_budget_vs_actual(
    mes: int,
    ano: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = ReportService(db)
    return await service.budget_vs_actual(current_user.id, mes, ano)