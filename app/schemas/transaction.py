from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from uuid import UUID
from datetime import datetime, date
from decimal import Decimal
from app.models.enums import TransactionType, TransactionStatus


class TransactionBase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    conta_id: UUID
    conta_destino_id: Optional[UUID] = None
    categoria_id: Optional[UUID] = None
    tipo: TransactionType
    valor: Decimal = Field(..., gt=0, decimal_places=2)
    data: date
    descricao: str = Field(..., min_length=1, max_length=200)
    observacoes: Optional[str] = None
    status: TransactionStatus = TransactionStatus.CONFIRMADO
    anexo_url: Optional[str] = Field(None, max_length=500)
    recorrencia_id: Optional[UUID] = None
    idempotency_key: Optional[UUID] = None


class TransactionCreate(TransactionBase):
    pass


class TransactionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    conta_id: Optional[UUID] = None
    conta_destino_id: Optional[UUID] = None
    categoria_id: Optional[UUID] = None
    tipo: Optional[TransactionType] = None
    valor: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    data: Optional[date] = None
    descricao: Optional[str] = Field(None, min_length=1, max_length=200)
    observacoes: Optional[str] = None
    status: Optional[TransactionStatus] = None
    anexo_url: Optional[str] = Field(None, max_length=500)


class TransactionResponse(TransactionBase):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: UUID
    user_id: UUID
    criado_em: datetime
    atualizado_em: datetime


class TransactionFilters(BaseModel):
    model_config = ConfigDict(extra="forbid")
    conta_id: Optional[UUID] = None
    categoria_id: Optional[UUID] = None
    tipo: Optional[TransactionType] = None
    status: Optional[TransactionStatus] = None
    data_inicio: Optional[date] = None
    data_fim: Optional[date] = None
    descricao: Optional[str] = None