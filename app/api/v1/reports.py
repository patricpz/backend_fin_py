from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional, Union, List
from app.db.session import get_db
from app.core.deps import get_current_user
from app.schemas.report import (
    MonthlySummary,
    CategorySpendingReport,
    BalanceEvolutionReport,
    MonthlyBalanceEvolution,
    BudgetVsActualReport,
)
from app.services.report_service import ReportService
from app.models.user import User


router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/monthly-summary", response_model=MonthlySummary)
async def get_monthly_summary(
    mes: Optional[int] = Query(None),
    month: Optional[int] = Query(None),
    ano: Optional[int] = Query(None),
    year: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    m = mes if mes is not None else month
    y = ano if ano is not None else year
    if m is None or y is None:
        from app.core.exceptions import BusinessRuleError
        raise BusinessRuleError("mes and ano parameters are required", "MISSING_PARAMS")
    service = ReportService(db)
    return await service.monthly_summary(current_user.id, m, y)


@router.get("/category-spending", response_model=CategorySpendingReport)
async def get_category_spending(
    mes: Optional[int] = Query(None),
    month: Optional[int] = Query(None),
    ano: Optional[int] = Query(None),
    year: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    m = mes if mes is not None else month
    y = ano if ano is not None else year
    if m is None or y is None:
        from app.core.exceptions import BusinessRuleError
        raise BusinessRuleError("mes and ano parameters are required", "MISSING_PARAMS")
    service = ReportService(db)
    return await service.category_spending(current_user.id, m, y)


@router.get("/balance-evolution", response_model=Union[BalanceEvolutionReport, List[MonthlyBalanceEvolution]])
async def get_balance_evolution(
    ano: Optional[int] = Query(None),
    year: Optional[int] = Query(None),
    mes: Optional[int] = Query(None),
    month: Optional[int] = Query(None),
    conta_id: Optional[UUID] = Query(None),
    account_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    y = ano if ano is not None else year
    m = mes if mes is not None else month
    acc_id = conta_id or account_id
    if y is None:
        from app.core.exceptions import BusinessRuleError
        raise BusinessRuleError("ano parameter is required", "MISSING_PARAMS")

    service = ReportService(db)
    if m is not None and acc_id is not None:
        return await service.balance_evolution_daily(current_user.id, acc_id, m, y)
    return await service.balance_evolution_yearly(current_user.id, y, acc_id)


@router.get("/budget-vs-actual", response_model=BudgetVsActualReport)
async def get_budget_vs_actual(
    mes: Optional[int] = Query(None),
    month: Optional[int] = Query(None),
    ano: Optional[int] = Query(None),
    year: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    m = mes if mes is not None else month
    y = ano if ano is not None else year
    if m is None or y is None:
        from app.core.exceptions import BusinessRuleError
        raise BusinessRuleError("mes and ano parameters are required", "MISSING_PARAMS")
    service = ReportService(db)
    return await service.budget_vs_actual(current_user.id, m, y)
