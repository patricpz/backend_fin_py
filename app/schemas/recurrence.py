from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import date, datetime
from decimal import Decimal
from app.models.enums import TransactionType, RecurrenceFrequency


class RecurrenceBase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    conta_id: UUID
    categoria_id: Optional[UUID] = None
    tipo: TransactionType
    valor: Decimal = Field(..., gt=0, decimal_places=2)
    frequencia: RecurrenceFrequency
    dia_do_mes: Optional[int] = Field(None, ge=1, le=31)
    dia_semana: Optional[int] = Field(None, ge=0, le=6)
    data_inicio: date
    data_fim: Optional[date] = None
    descricao: str = Field(..., min_length=1, max_length=200)


class RecurrenceCreate(RecurrenceBase):
    pass


class RecurrenceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    conta_id: Optional[UUID] = None
    categoria_id: Optional[UUID] = None
    tipo: Optional[TransactionType] = None
    valor: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    frequencia: Optional[RecurrenceFrequency] = None
    dia_do_mes: Optional[int] = Field(None, ge=1, le=31)
    dia_semana: Optional[int] = Field(None, ge=0, le=6)
    data_inicio: Optional[date] = None
    data_fim: Optional[date] = None
    descricao: Optional[str] = Field(None, min_length=1, max_length=200)
    ativo: Optional[bool] = None


class RecurrenceResponse(RecurrenceBase):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: UUID
    user_id: UUID
    proxima_execucao: date
    ativo: bool
    criado_em: datetime
    atualizado_em: datetime


class RecurrenceGenerateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    geradas: int
    message: str