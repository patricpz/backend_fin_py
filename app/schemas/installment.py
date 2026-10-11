from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID
from decimal import Decimal
from datetime import date


class InstallmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    numero_parcelas: int = Field(..., ge=2, le=24)
    data_inicio: date
    valor_por_parcela: Decimal | None = Field(None, gt=0, decimal_places=2)


class InstallmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: UUID
    transaction_id: UUID
    parcela_numero: int
    valor: Decimal
    data_vencimento: date
    status: str
    observacoes: str | None
