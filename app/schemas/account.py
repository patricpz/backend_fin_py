from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime, date
from decimal import Decimal
from app.models.enums import AccountType


class AccountBase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nome: str = Field(..., min_length=1, max_length=120)
    tipo: AccountType
    saldo_inicial: Decimal = Field(default=Decimal("0"), ge=0, decimal_places=2)
    moeda: str = Field(default="BRL", min_length=3, max_length=3)


class AccountCreate(AccountBase):
    pass


class AccountUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nome: Optional[str] = Field(None, min_length=1, max_length=120)
    tipo: Optional[AccountType] = None
    saldo_inicial: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    moeda: Optional[str] = Field(None, min_length=3, max_length=3)
    ativo: Optional[bool] = None


class AccountResponse(AccountBase):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: UUID
    user_id: UUID
    ativo: bool
    criado_em: datetime
    atualizado_em: datetime
    saldo_atual: Decimal


class AccountWithBalance(AccountResponse):
    pass