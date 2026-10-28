from pydantic import BaseModel, Field, ConfigDict, AliasChoices, computed_field
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from app.models.enums import CategoryType


class CategoryBase(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)
    nome: str = Field(..., validation_alias=AliasChoices("nome", "name"), min_length=1, max_length=100)
    tipo: CategoryType = Field(..., validation_alias=AliasChoices("tipo", "type"))
    cor: str = Field(default="#6366F1", validation_alias=AliasChoices("cor", "color"))
    icone: str = Field(default="Tag", validation_alias=AliasChoices("icone", "icon"), max_length=60)
    categoria_pai_id: Optional[UUID] = Field(default=None, validation_alias=AliasChoices("categoria_pai_id", "parent_id", "parentId"))


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)
    nome: Optional[str] = Field(None, validation_alias=AliasChoices("nome", "name"), min_length=1, max_length=100)
    tipo: Optional[CategoryType] = Field(None, validation_alias=AliasChoices("tipo", "type"))
    cor: Optional[str] = Field(None, validation_alias=AliasChoices("cor", "color"))
    icone: Optional[str] = Field(None, validation_alias=AliasChoices("icone", "icon"), max_length=60)
    categoria_pai_id: Optional[UUID] = Field(None, validation_alias=AliasChoices("categoria_pai_id", "parent_id", "parentId"))
    ativo: Optional[bool] = Field(None, validation_alias=AliasChoices("ativo", "active"))


class CategoryResponse(CategoryBase):
    model_config = ConfigDict(from_attributes=True, extra="ignore", populate_by_name=True)
    id: UUID
    user_id: UUID
    ativo: bool
    criado_em: datetime
    atualizado_em: datetime

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
    def color(self) -> str:
        return self.cor

    @computed_field
    @property
    def icon(self) -> str:
        return self.icone

    @computed_field
    @property
    def parentId(self) -> Optional[UUID]:
        return self.categoria_pai_id

    @computed_field
    @property
    def userId(self) -> UUID:
        return self.user_id

    @computed_field
    @property
    def active(self) -> bool:
        return self.ativo

    @computed_field
    @property
    def createdAt(self) -> datetime:
        return self.criado_em

    @computed_field
    @property
    def updatedAt(self) -> datetime:
        return self.atualizado_em


class CategoryTree(CategoryResponse):
    children: List["CategoryTree"] = []
    model_config = ConfigDict(from_attributes=True, extra="ignore", populate_by_name=True)


CategoryTree.model_rebuild()
