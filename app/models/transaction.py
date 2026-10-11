import uuid
from datetime import date
from sqlalchemy import String, Numeric, Date, Boolean, Text, ForeignKey, Index, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin, GUID
from app.models.enums import TransactionType, TransactionStatus


class Transaction(Base, TimestampMixin):
    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    conta_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False, index=True)
    conta_destino_id: Mapped[uuid.UUID | None] = mapped_column(GUID, ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=True)
    categoria_id: Mapped[uuid.UUID | None] = mapped_column(GUID, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    tipo: Mapped[TransactionType] = mapped_column(String(20), nullable=False)
    valor: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    installments_total_count: Mapped[int | None] = mapped_column(nullable=True)
    data: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    descricao: Mapped[str] = mapped_column(String(200), nullable=False)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[TransactionStatus] = mapped_column(String(20), default=TransactionStatus.CONFIRMADO, nullable=False)
    anexo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    recorrencia_id: Mapped[uuid.UUID | None] = mapped_column(GUID, ForeignKey("recurring_transactions.id", ondelete="SET NULL"), nullable=True)
    idempotency_key: Mapped[uuid.UUID | None] = mapped_column(GUID, nullable=True, unique=True)

    user = relationship("User", back_populates="transactions")
    account = relationship("Account", back_populates="transactions", foreign_keys=[conta_id])
    account_destino = relationship("Account", back_populates="transactions_destino", foreign_keys=[conta_destino_id])
    category = relationship("Category", back_populates="transactions")
    recurrence = relationship("RecurringTransaction", back_populates="generated_transactions")
    installments = relationship("Installment", back_populates="transaction", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("valor > 0", name="ck_transactions_valor_positive"),
        Index("ix_transactions_user_data_desc", "user_id", "data"),
        Index("ix_transactions_conta_data", "conta_id", "data"),
        Index("ix_transactions_categoria_data", "categoria_id", "data"),
        Index("ix_transactions_status_data", "status", "data"),
    )