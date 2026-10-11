import uuid
from datetime import date
from sqlalchemy import String, Date, ForeignKey, Index, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin, GUID
from app.models.enums import TransactionStatus


class Installment(Base, TimestampMixin):
    __tablename__ = "installments"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    parcela_numero: Mapped[int] = mapped_column(nullable=False)
    valor: Mapped[float] = mapped_column(nullable=False)
    data_vencimento: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[TransactionStatus] = mapped_column(String(20), default=TransactionStatus.PENDENTE, nullable=False)
    observacoes: Mapped[str | None] = mapped_column(String(500), nullable=True)

    transaction = relationship("Transaction", back_populates="installments")

    __table_args__ = (
        Index("ix_installments_transaction_parcela", "transaction_id", "parcela_numero", unique=True),
        CheckConstraint("parcela_numero > 0", name="ck_installments_parcela_numero_positive"),
    )
