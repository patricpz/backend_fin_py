from pydantic import BaseModel, Field, ConfigDict, AliasChoices, computed_field
from typing import Optional
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from app.models.enums import AccountType


class AccountBase(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)
    nome: str = Field(..., validation_alias=AliasChoices("nome", "name"), min_length=1, max_length=120)
    tipo: AccountType = Field(..., validation_alias=AliasChoices("tipo", "type"))
    saldo_inicial: Decimal = Field(default=Decimal("0"), validation_alias=AliasChoices("saldo_inicial", "initial_balance", "initialBalance"), ge=0, decimal_places=2)
    moeda: str = Field(default="BRL", validation_alias=AliasChoices("moeda", "currency"), min_length=3, max_length=3)


class AccountCreate(AccountBase):
    pass


class AccountUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)
    nome: Optional[str] = Field(None, validation_alias=AliasChoices("nome", "name"), min_length=1, max_length=120)
    tipo: Optional[AccountType] = Field(None, validation_alias=AliasChoices("tipo", "type"))
    saldo_inicial: Optional[Decimal] = Field(None, validation_alias=AliasChoices("saldo_inicial", "initial_balance", "initialBalance"), ge=0, decimal_places=2)
    moeda: Optional[str] = Field(None, validation_alias=AliasChoices("moeda", "currency"), min_length=3, max_length=3)
    ativo: Optional[bool] = Field(None, validation_alias=AliasChoices("ativo", "active"))


class AccountResponse(AccountBase):
    model_config = ConfigDict(from_attributes=True, extra="ignore", populate_by_name=True)
    id: UUID
    user_id: UUID
    ativo: bool
    criado_em: datetime
    atualizado_em: datetime
    saldo_atual: Decimal

    @computed_field
    @property
    def balance(self) -> Decimal:
        return self.saldo_atual

    @computed_field
    @property
    def name(self) -> str:
        return self.nome

    @computed_field
    @property
    def type(self) -> str:
        return self.tipo.value if hasattr(self.tipo, "value") else str(self.tipo)

    @computed_field
    @property
    def initialBalance(self) -> Decimal:
        return self.saldo_inicial

    @computed_field
    @property
    def currency(self) -> str:
        return self.moeda

    @computed_field
    @property
    def active(self) -> bool:
        return self.ativo

    @computed_field
    @property
    def userId(self) -> UUID:
        return self.user_id

    @computed_field
    @property
    def createdAt(self) -> datetime:
        return self.criado_em

    @computed_field
    @property
    def updatedAt(self) -> datetime:
        return self.atualizado_em


class AccountWithBalance(AccountResponse):
    pass
