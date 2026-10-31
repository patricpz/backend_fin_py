from pydantic import BaseModel, Field, ConfigDict, model_validator
from typing import Optional
from uuid import UUID
from datetime import date as dt_date
from decimal import Decimal


class ExpenseInstallmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")
    id: UUID
    description: str
    category: Optional[str] = None
    total_amount: Decimal
    installment_count: int
    installment_amount: Decimal
    paid_installments: int
    remaining_installments: int
    progress_percent: int
    paid_amount: Decimal
    remaining_amount: Decimal
    first_due_date: dt_date
    next_due_date: Optional[dt_date] = None
    is_completed: bool


class ExpenseInstallmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    description: str = Field(..., min_length=1, max_length=200)
    category: Optional[str] = Field(None, max_length=100)
    total_amount: Decimal = Field(..., gt=0, decimal_places=2)
    installment_count: int = Field(..., ge=2, le=120)
    first_due_date: dt_date
    paid_installments: Optional[int] = None

    @model_validator(mode="after")
    def reject_paid_installments_on_create(self):
        if self.paid_installments is not None and self.paid_installments != 0:
            raise ValueError("paid_installments não é aceito na criação de despesa parcelada")
        return self


class ExpenseInstallmentPayCorrectionRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    paid_installments: int = Field(..., ge=0)
