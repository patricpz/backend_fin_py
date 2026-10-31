from pydantic import BaseModel, Field, ConfigDict, model_validator, AliasChoices, computed_field
from typing import Optional, List
from uuid import UUID
from datetime import datetime, date as dt_date
from decimal import Decimal
from app.models.enums import TransactionType, TransactionStatus


class InstallmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore", populate_by_name=True)
    id: UUID
    transaction_id: UUID
    parcela_numero: int
    valor: Decimal
    data_vencimento: dt_date
    status: str
    observacoes: str | None


class InstallmentPayRequest(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)
    paid_installments: Optional[int] = Field(None, ge=0, le=24, validation_alias=AliasChoices("paid_installments", "paidInstallments"))


class TransactionBase(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)
    conta_id: UUID = Field(..., validation_alias=AliasChoices("conta_id", "accountId", "account_id"))
    conta_destino_id: Optional[UUID] = Field(None, validation_alias=AliasChoices("conta_destino_id", "destinationAccountId", "destination_account_id"))
    categoria_id: Optional[UUID] = Field(None, validation_alias=AliasChoices("categoria_id", "categoryId", "category_id"))
    tipo: TransactionType = Field(default=TransactionType.DESPESA, validation_alias=AliasChoices("tipo", "type"))
    valor: Decimal = Field(..., gt=0, decimal_places=2, validation_alias=AliasChoices("valor", "totalAmount", "total_amount", "amount"))
    data: dt_date = Field(default_factory=dt_date.today, validation_alias=AliasChoices("data", "date"))
    descricao: str = Field(..., min_length=1, max_length=200, validation_alias=AliasChoices("descricao", "description"))
    observacoes: Optional[str] = Field(None, validation_alias=AliasChoices("observacoes", "notes", "observation"))
    status: TransactionStatus = TransactionStatus.CONFIRMADO
    anexo_url: Optional[str] = Field(None, max_length=500, validation_alias=AliasChoices("anexo_url", "attachmentUrl"))
    recorrencia_id: Optional[UUID] = None
    idempotency_key: Optional[UUID] = None
    is_installment: bool = Field(default=False, validation_alias=AliasChoices("is_installment", "isInstallment"))
    installment_count: Optional[int] = Field(default=None, ge=2, le=24, validation_alias=AliasChoices("installment_count", "installmentCount"))
    paid_installments: int = Field(default=0, ge=0, validation_alias=AliasChoices("paid_installments", "paidInstallments"))
    first_due_date: Optional[dt_date] = Field(default=None, validation_alias=AliasChoices("first_due_date", "firstDueDate"))

    @model_validator(mode="after")
    def validate_installment_rules(self):
        if self.is_installment:
            if self.tipo != TransactionType.DESPESA:
                raise ValueError("Despesas parceladas só são permitidas para tipo 'despesa'")
            if self.installment_count is None or self.installment_count < 2:
                raise ValueError("installment_count deve ser >= 2 para despesas parceladas")
            if self.first_due_date is None:
                raise ValueError("first_due_date é obrigatório para despesas parceladas")
            if self.paid_installments < 0:
                raise ValueError("paid_installments não pode ser negativo")
            if self.paid_installments > self.installment_count:
                raise ValueError("paid_installments não pode exceder installment_count")
        return self


class TransactionCreate(TransactionBase):
    pass


class TransactionUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)
    conta_id: Optional[UUID] = Field(None, validation_alias=AliasChoices("conta_id", "accountId", "account_id"))
    conta_destino_id: Optional[UUID] = Field(None, validation_alias=AliasChoices("conta_destino_id", "destinationAccountId", "destination_account_id"))
    categoria_id: Optional[UUID] = Field(None, validation_alias=AliasChoices("categoria_id", "categoryId", "category_id"))
    tipo: Optional[TransactionType] = Field(None, validation_alias=AliasChoices("tipo", "type"))
    valor: Optional[Decimal] = Field(None, gt=0, decimal_places=2, validation_alias=AliasChoices("valor", "totalAmount", "total_amount", "amount"))
    data: Optional[dt_date] = Field(None, validation_alias=AliasChoices("data", "date"))
    descricao: Optional[str] = Field(None, min_length=1, max_length=200, validation_alias=AliasChoices("descricao", "description"))
    observacoes: Optional[str] = Field(None, validation_alias=AliasChoices("observacoes", "notes", "observation"))
    status: Optional[TransactionStatus] = None
    anexo_url: Optional[str] = Field(None, max_length=500, validation_alias=AliasChoices("anexo_url", "attachmentUrl"))
    is_installment: Optional[bool] = Field(None, validation_alias=AliasChoices("is_installment", "isInstallment"))
    installment_count: Optional[int] = Field(None, ge=2, le=24, validation_alias=AliasChoices("installment_count", "installmentCount"))
    paid_installments: Optional[int] = Field(None, ge=0, validation_alias=AliasChoices("paid_installments", "paidInstallments"))
    first_due_date: Optional[dt_date] = Field(None, validation_alias=AliasChoices("first_due_date", "firstDueDate"))


class TransactionResponse(TransactionBase):
    model_config = ConfigDict(from_attributes=True, extra="ignore", populate_by_name=True)
    id: UUID
    user_id: UUID
    criado_em: datetime
    atualizado_em: datetime
    installments_total_count: Optional[int] = None
    installment_amount: Optional[Decimal] = None
    remaining_installments: Optional[int] = None
    progress_percent: Optional[int] = None
    paid_amount: Optional[Decimal] = None
    remaining_amount: Optional[Decimal] = None
    next_due_date: Optional[dt_date] = None
    is_completed: Optional[bool] = None
    installment_display: Optional[str] = None
    progress_display: Optional[str] = None

    @computed_field
    @property
    def description(self) -> str:
        return self.descricao

    @computed_field
    @property
    def type(self) -> str:
        return self.tipo.value if hasattr(self.tipo, "value") else str(self.tipo)

    @computed_field
    @property
    def date(self) -> dt_date:
        return self.data

    @computed_field
    @property
    def accountId(self) -> UUID:
        return self.conta_id

    @computed_field
    @property
    def destinationAccountId(self) -> Optional[UUID]:
        return self.conta_destino_id

    @computed_field
    @property
    def categoryId(self) -> Optional[UUID]:
        return self.categoria_id

    @computed_field
    @property
    def signed_amount(self) -> Decimal:
        if self.tipo in (TransactionType.DESPESA, TransactionType.TRANSFERENCIA):
            return -abs(self.valor)
        return abs(self.valor)

    @computed_field
    @property
    def signedAmount(self) -> Decimal:
        return self.signed_amount

    @computed_field
    @property
    def valor_com_sinal(self) -> Decimal:
        return self.signed_amount

    @computed_field
    @property
    def amount(self) -> Decimal:
        return self.signed_amount

    @computed_field
    @property
    def totalAmount(self) -> Decimal:
        return self.valor

    @computed_field
    @property
    def isInstallment(self) -> bool:
        return self.is_installment

    @computed_field
    @property
    def installmentCount(self) -> Optional[int]:
        return self.installment_count

    @computed_field
    @property
    def installmentAmount(self) -> Optional[Decimal]:
        return self.installment_amount

    @computed_field
    @property
    def paidInstallments(self) -> int:
        return self.paid_installments

    @computed_field
    @property
    def remainingInstallments(self) -> Optional[int]:
        return self.remaining_installments

    @computed_field
    @property
    def progressPercent(self) -> Optional[int]:
        return self.progress_percent

    @computed_field
    @property
    def paidAmount(self) -> Optional[Decimal]:
        return self.paid_amount

    @computed_field
    @property
    def remainingAmount(self) -> Optional[Decimal]:
        return self.remaining_amount

    @computed_field
    @property
    def nextDueDate(self) -> Optional[dt_date]:
        return self.next_due_date

    @computed_field
    @property
    def isCompleted(self) -> Optional[bool]:
        return self.is_completed

    @computed_field
    @property
    def firstDueDate(self) -> Optional[dt_date]:
        return self.first_due_date

    @computed_field
    @property
    def installmentDisplay(self) -> Optional[str]:
        return self.installment_display

    @computed_field
    @property
    def progressDisplay(self) -> Optional[str]:
        return self.progress_display


class TransactionResponseWithInstallments(TransactionResponse):
    model_config = ConfigDict(from_attributes=True, extra="ignore", populate_by_name=True)
    installments: List[InstallmentResponse]


class TransactionFilters(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)
    conta_id: Optional[UUID] = Field(None, validation_alias=AliasChoices("conta_id", "accountId", "account_id"))
    categoria_id: Optional[UUID] = Field(None, validation_alias=AliasChoices("categoria_id", "categoryId", "category_id"))
    tipo: Optional[TransactionType] = Field(None, validation_alias=AliasChoices("tipo", "type"))
    status: Optional[TransactionStatus] = None
    data_inicio: Optional[dt_date] = Field(None, validation_alias=AliasChoices("data_inicio", "startDate", "start_date"))
    data_fim: Optional[dt_date] = Field(None, validation_alias=AliasChoices("data_fim", "endDate", "end_date"))
    descricao: Optional[str] = Field(None, validation_alias=AliasChoices("descricao", "description"))
    is_installment: Optional[bool] = Field(None, validation_alias=AliasChoices("is_installment", "isInstallment"))
    completed: Optional[bool] = None


class TransactionInstallmentResponse(TransactionResponse):
    """Card para despesas parceladas com campos derivados de progresso."""
    pass


class InstallmentsSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)
    total_despesas_parceladas: int = Field(..., validation_alias=AliasChoices("total_despesas_parceladas", "totalInstallmentsCount"))
    ativas_count: int = Field(..., validation_alias=AliasChoices("ativas_count", "activeCount"))
    concluidas_count: int = Field(..., validation_alias=AliasChoices("concluidas_count", "completedCount"))
    valor_total_original: Decimal = Field(..., validation_alias=AliasChoices("valor_total_original", "totalAmount"))
    valor_total_pago: Decimal = Field(..., validation_alias=AliasChoices("valor_total_pago", "totalPaidAmount"))
    valor_total_restante: Decimal = Field(..., validation_alias=AliasChoices("valor_total_restante", "totalRemainingAmount"))
    total_parcelas: int = Field(..., validation_alias=AliasChoices("total_parcelas", "totalInstallments"))
    total_parcelas_pagas: int = Field(..., validation_alias=AliasChoices("total_parcelas_pagas", "totalPaidInstallments"))
    total_parcelas_restantes: int = Field(..., validation_alias=AliasChoices("total_parcelas_restantes", "totalRemainingInstallments"))
    percentual_geral_pago: int = Field(..., validation_alias=AliasChoices("percentual_geral_pago", "overallProgressPercent"))
    proximo_vencimento: Optional[dt_date] = Field(None, validation_alias=AliasChoices("proximo_vencimento", "nextDueDate"))

    @computed_field
    @property
    def totalInstallmentsCount(self) -> int:
        return self.total_despesas_parceladas

    @computed_field
    @property
    def activeCount(self) -> int:
        return self.ativas_count

    @computed_field
    @property
    def completedCount(self) -> int:
        return self.concluidas_count

    @computed_field
    @property
    def totalAmount(self) -> Decimal:
        return self.valor_total_original

    @computed_field
    @property
    def totalPaidAmount(self) -> Decimal:
        return self.valor_total_pago

    @computed_field
    @property
    def totalRemainingAmount(self) -> Decimal:
        return self.valor_total_restante

    @computed_field
    @property
    def totalInstallments(self) -> int:
        return self.total_parcelas

    @computed_field
    @property
    def totalPaidInstallments(self) -> int:
        return self.total_parcelas_pagas

    @computed_field
    @property
    def totalRemainingInstallments(self) -> int:
        return self.total_parcelas_restantes

    @computed_field
    @property
    def overallProgressPercent(self) -> int:
        return self.percentual_geral_pago

    @computed_field
    @property
    def nextDueDate(self) -> Optional[dt_date]:
        return self.proximo_vencimento
