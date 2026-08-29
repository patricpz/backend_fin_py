from typing import Generic, TypeVar, Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from uuid import UUID

T = TypeVar("T")


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    detail: str
    code: str


class Page(BaseModel, Generic[T]):
    model_config = ConfigDict(extra="forbid")
    items: list[T]
    total: int
    page: int
    size: int
    pages: int

    @classmethod
    def create(cls, items: list[T], total: int, page: int, size: int) -> "Page[T]":
        pages = (total + size - 1) // size if size > 0 else 0
        return cls(items=items, total=total, page=page, size=size, pages=pages)


class IDResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID