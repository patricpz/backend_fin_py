from pydantic import BaseModel, Field, ConfigDict, AliasChoices, computed_field
from typing import Optional
from uuid import UUID
from datetime import date, datetime
from decimal import Decimal
from app.models.enums import GoalStatus, GoalContributionType


class GoalBase(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)
    nome: str = Field(..., validation_alias=AliasChoices("nome", "name"), min_length=1, max_length=150)
    descricao: Optional[str] = Field(None, validation_alias=AliasChoices("descricao", "description"), max_length=500)
    valor_alvo: Decimal = Field(..., validation_alias=AliasChoices("valor_alvo", "target_amount", "targetAmount"), gt=0, decimal_places=2)
    data_alvo: Optional[date] = Field(None, validation_alias=AliasChoices("data_alvo", "target_date", "targetDate"))
    categoria: Optional[str] = Field(None, validation_alias=AliasChoices("categoria", "category"), max_length=100)


class GoalCreate(GoalBase):
    pass


class GoalUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)
    nome: Optional[str] = Field(None, validation_alias=AliasChoices("nome", "name"), min_length=1, max_length=150)
    descricao: Optional[str] = Field(None, validation_alias=AliasChoices("descricao", "description"), max_length=500)
    valor_alvo: Optional[Decimal] = Field(None, validation_alias=AliasChoices("valor_alvo", "target_amount", "targetAmount"), gt=0, decimal_places=2)
    data_alvo: Optional[date] = Field(None, validation_alias=AliasChoices("data_alvo", "target_date", "targetDate"))
    categoria: Optional[str] = Field(None, validation_alias=AliasChoices("categoria", "category"), max_length=100)
    status: Optional[GoalStatus] = None


class GoalResponse(GoalBase):
    model_config = ConfigDict(from_attributes=True, extra="ignore", populate_by_name=True)
    id: UUID
    user_id: UUID
    status: GoalStatus
    valor_atual: Decimal
    progresso_percentual: float
    criado_em: datetime
    atualizado_em: datetime

    @computed_field
    @property
    def userId(self) -> UUID:
        return self.user_id

    @computed_field
    @property
    def name(self) -> str:
        return self.nome

    @computed_field
    @property
    def description(self) -> Optional[str]:
        return self.descricao

    @computed_field
    @property
    def targetAmount(self) -> Decimal:
        return self.valor_alvo

    @computed_field
    @property
    def currentAmount(self) -> Decimal:
        return self.valor_atual

    @computed_field
    @property
    def progressPercentage(self) -> float:
        return self.progresso_percentual

    @computed_field
    @property
    def targetDate(self) -> Optional[date]:
        return self.data_alvo

    @computed_field
    @property
    def category(self) -> Optional[str]:
        return self.categoria

    @computed_field
    @property
    def createdAt(self) -> datetime:
        return self.criado_em

    @computed_field
    @property
    def updatedAt(self) -> datetime:
        return self.atualizado_em


class GoalProgressResponse(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)
    goal_id: UUID
    valor_alvo: Decimal
    valor_atual: Decimal
    progresso_percentual: float
    status: str

    @computed_field
    @property
    def goalId(self) -> UUID:
        return self.goal_id

    @computed_field
    @property
    def targetAmount(self) -> Decimal:
        return self.valor_alvo

    @computed_field
    @property
    def currentAmount(self) -> Decimal:
        return self.valor_atual

    @computed_field
    @property
    def progressPercentage(self) -> float:
        return self.progresso_percentual


class GoalContributionBase(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)
    valor: Decimal = Field(..., validation_alias=AliasChoices("valor", "amount"), gt=0, decimal_places=2)
    tipo: GoalContributionType = Field(..., validation_alias=AliasChoices("tipo", "type"))
    data: date = Field(..., validation_alias=AliasChoices("data", "date"))
    observacao: Optional[str] = Field(None, validation_alias=AliasChoices("observacao", "observation"), max_length=200)


class GoalContributionCreate(GoalContributionBase):
    pass


class GoalContributionResponse(GoalContributionBase):
    model_config = ConfigDict(from_attributes=True, extra="ignore", populate_by_name=True)
    id: UUID
    goal_id: UUID
    criado_em: datetime

    @computed_field
    @property
    def goalId(self) -> UUID:
        return self.goal_id

    @computed_field
    @property
    def amount(self) -> Decimal:
        return self.valor

    @computed_field
    @property
    def type(self) -> str:
        return self.tipo.value if hasattr(self.tipo, "value") else str(self.tipo)

    @computed_field
    @property
    def date(self) -> date:
        return self.data

    @computed_field
    @property
    def observation(self) -> Optional[str]:
        return self.observacao

    @computed_field
    @property
    def createdAt(self) -> datetime:
        return self.criado_em
