from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import List, Optional
from app.db.session import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.expense import (
    ExpenseInstallmentResponse,
    ExpenseInstallmentCreate,
    ExpenseInstallmentPayCorrectionRequest,
)
from app.services.expense_service import ExpenseService

router = APIRouter(prefix="/expenses", tags=["expenses"])


# 1. Rota declarada antes de /{id} para não colidir
@router.get("/installments", response_model=List[ExpenseInstallmentResponse])
async def list_installments(
    include_completed: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ExpenseService(db)
    return await service.list_installments(current_user.id, include_completed=include_completed)


# 2. Criação de despesa parcelada via /expenses/installments ou /expenses
@router.post("/installments", response_model=ExpenseInstallmentResponse, status_code=status.HTTP_201_CREATED)
@router.post("", response_model=ExpenseInstallmentResponse, status_code=status.HTTP_201_CREATED)
async def create_installment_expense(
    data: ExpenseInstallmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ExpenseService(db)
    return await service.create_installment_expense(current_user.id, data)


# 3. Pagar parcela
@router.patch("/{id}/installments/pay", response_model=ExpenseInstallmentResponse)
async def pay_installment(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ExpenseService(db)
    return await service.pay_installment(current_user.id, id)


# 4. Correção manual de parcelas pagas
@router.patch("/{id}/installments", response_model=ExpenseInstallmentResponse)
async def update_paid_installments(
    id: UUID,
    data: ExpenseInstallmentPayCorrectionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ExpenseService(db)
    return await service.update_paid_installments(current_user.id, id, data.paid_installments)
