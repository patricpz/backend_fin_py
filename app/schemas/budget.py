from pydantic import BaseModel, Field, ConfigDict, AliasChoices, computed_field
from typing import Optional
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from app.models.enums import BudgetAlertPercent


class BudgetBase(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)
    categoria_id: UUID = Field(..., validation_alias=AliasChoices("categoria_id", "category_id", "categoryId"))
    valor_limite: Decimal = Field(..., validation_alias=AliasChoices("valor_limite", "limit_amount", "limitAmount"), ge=0, decimal_places=2)
    mes: int = Field(..., validation_alias=AliasChoices("mes", "month"), ge=1, le=12)
    ano: int = Field(..., validation_alias=AliasChoices("ano", "year"), ge=2000)
    alerta_percentual: int = Field(
        default=BudgetAlertPercent.DEFAULT,
        validation_alias=AliasChoices("alerta_percentual", "percentual_alerta", "alert_percentage", "alertPercentage"),
        ge=1,
        le=100
    )


class BudgetCreate(BudgetBase):
    pass


class BudgetUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)
    valor_limite: Optional[Decimal] = Field(None, validation_alias=AliasChoices("valor_limite", "limit_amount", "limitAmount"), ge=0, decimal_places=2)
    alerta_percentual: Optional[int] = Field(
        None,
        validation_alias=AliasChoices("alerta_percentual", "percentual_alerta", "alert_percentage", "alertPercentage"),
        ge=1,
        le=100
    )


class BudgetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore", populate_by_name=True)
    id: UUID
    user_id: UUID
    categoria_id: UUID
    categoria_nome: Optional[str] = None
    valor_limite: Decimal
    valor_gasto: Optional[Decimal] = None
    percentual: Optional[float] = None
    alerta: Optional[bool] = None
    mes: int
    ano: int
    alerta_percentual: int
    criado_em: Optional[datetime] = None
    atualizado_em: Optional[datetime] = None

    @computed_field
    @property
    def userId(self) -> UUID:
        return self.user_id

    @computed_field
    @property
    def categoryId(self) -> UUID:
        return self.categoria_id

    @computed_field
    @property
    def categoryName(self) -> str:
        return self.categoria_nome or ""

    @computed_field
    @property
    def limitAmount(self) -> Decimal:
        return self.valor_limite

    @computed_field
    @property
    def spent(self) -> Decimal:
        return self.valor_gasto if self.valor_gasto is not None else Decimal("0.00")

    @computed_field
    @property
    def percentage(self) -> float:
        return self.percentual if self.percentual is not None else 0.0

    @computed_field
    @property
    def alertPercentage(self) -> int:
        return self.alerta_percentual

    @computed_field
    @property
    def alert(self) -> bool:
        return self.alerta if self.alerta is not None else False

    @computed_field
    @property
    def month(self) -> int:
        return self.mes

    @computed_field
    @property
    def year(self) -> int:
        return self.ano

    @computed_field
    @property
    def createdAt(self) -> Optional[datetime]:
        return self.criado_em

    @computed_field
    @property
    def updatedAt(self) -> Optional[datetime]:
        return self.atualizado_em


class BudgetProgress(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)
    budget_id: UUID
    categoria_id: UUID
    categoria_nome: str
    valor_limite: Decimal
    valor_gasto: Decimal
    percentual: float
    alerta: bool
    mes: int
    ano: int

    @computed_field
    @property
    def budgetId(self) -> UUID:
        return self.budget_id

    @computed_field
    @property
    def categoryId(self) -> UUID:
        return self.categoria_id

    @computed_field
    @property
    def categoryName(self) -> str:
        return self.categoria_nome

    @computed_field
    @property
    def limitAmount(self) -> Decimal:
        return self.valor_limite

    @computed_field
    @property
    def spent(self) -> Decimal:
        return self.valor_gasto

    @computed_field
    @property
    def percentage(self) -> float:
        return self.percentual

    @computed_field
    @property
    def alert(self) -> bool:
        return self.alerta

    @computed_field
    @property
    def month(self) -> int:
        return self.mes

    @computed_field
    @property
    def year(self) -> int:
        return self.ano
