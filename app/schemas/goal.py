from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import date, datetime
from decimal import Decimal
from app.models.enums import GoalStatus, GoalContributionType


class GoalBase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nome: str = Field(..., min_length=1, max_length=120)
    descricao: Optional[str] = Field(None, max_length=500)
    valor_alvo: Decimal = Field(..., gt=0, decimal_places=2)
    data_alvo: Optional[date] = None
    categoria: Optional[str] = Field(None, max_length=80)


class GoalCreate(GoalBase):
    pass


class GoalUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nome: Optional[str] = Field(None, min_length=1, max_length=120)
    descricao: Optional[str] = Field(None, max_length=500)
    valor_alvo: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    data_alvo: Optional[date] = None
    categoria: Optional[str] = Field(None, max_length=80)
    status: Optional[GoalStatus] = None


class GoalResponse(GoalBase):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: UUID
    user_id: UUID
    status: GoalStatus
    valor_atual: Decimal
    progresso_percentual: float
    criado_em: datetime
    atualizado_em: datetime


class GoalContributionBase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    valor: Decimal = Field(..., gt=0, decimal_places=2)
    tipo: GoalContributionType
    data: date
    observacao: Optional[str] = Field(None, max_length=200)


class GoalContributionCreate(GoalContributionBase):
    pass


class GoalContributionResponse(GoalContributionBase):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: UUID
    goal_id: UUID
    criado_em: datetime