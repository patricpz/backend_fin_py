from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from app.models.enums import BudgetAlertPercent


class BudgetBase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    categoria_id: UUID
    valor_limite: Decimal = Field(..., ge=0, decimal_places=2)
    mes: int = Field(..., ge=1, le=12)
    ano: int = Field(..., ge=2000)
    alerta_percentual: int = Field(default=BudgetAlertPercent.DEFAULT, ge=1, le=100)


class BudgetCreate(BudgetBase):
    pass


class BudgetUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    valor_limite: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    alerta_percentual: Optional[int] = Field(None, ge=1, le=100)


class BudgetResponse(BudgetBase):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: UUID
    user_id: UUID
    criado_em: datetime
    atualizado_em: datetime


class BudgetProgress(BaseModel):
    model_config = ConfigDict(extra="forbid")
    budget_id: UUID
    categoria_id: UUID
    categoria_nome: str
    valor_limite: Decimal
    valor_gasto: Decimal
    percentual: float
    alerta: bool
    mes: int
    ano: int