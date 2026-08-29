from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from app.models.enums import CategoryType


class CategoryBase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nome: str = Field(..., min_length=1, max_length=80)
    tipo: CategoryType
    cor: str = Field(default="#6366F1", pattern=r"^#[0-9A-Fa-f]{6}$")
    icone: str = Field(default="tag", max_length=40)
    categoria_pai_id: Optional[UUID] = None


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nome: Optional[str] = Field(None, min_length=1, max_length=80)
    tipo: Optional[CategoryType] = None
    cor: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    icone: Optional[str] = Field(None, max_length=40)
    categoria_pai_id: Optional[UUID] = None
    ativo: Optional[bool] = None


class CategoryResponse(CategoryBase):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: UUID
    user_id: UUID
    ativo: bool
    criado_em: datetime
    atualizado_em: datetime


class CategoryTree(CategoryResponse):
    children: List["CategoryTree"] = []

    model_config = ConfigDict(from_attributes=True, extra="forbid")


CategoryTree.model_rebuild()