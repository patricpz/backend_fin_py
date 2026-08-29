import uuid
from datetime import date
from sqlalchemy import String, Numeric, Date, Boolean, ForeignKey, SmallInteger, CheckConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin, GUID
from app.models.enums import TransactionType, RecurrenceFrequency


class RecurringTransaction(Base, TimestampMixin):
    __tablename__ = "recurring_transactions"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    conta_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    categoria_id: Mapped[uuid.UUID | None] = mapped_column(GUID, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    tipo: Mapped[TransactionType] = mapped_column(String(20), nullable=False)
    valor: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    frequencia: Mapped[RecurrenceFrequency] = mapped_column(String(20), nullable=False)
    dia_do_mes: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    dia_semana: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    data_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    data_fim: Mapped[date | None] = mapped_column(Date, nullable=True)
    proxima_execucao: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    descricao: Mapped[str] = mapped_column(String(200), nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user = relationship("User", back_populates="recurrences")
    account = relationship("Account", back_populates="recurrences")
    category = relationship("Category")
    generated_transactions = relationship("Transaction", back_populates="recurrence")

    __table_args__ = (
        CheckConstraint("valor > 0", name="ck_recurring_valor_positive"),
        CheckConstraint("frequencia IN ('diaria','semanal','mensal','anual')", name="ck_recurring_frequencia_valid"),
        CheckConstraint("(frequencia IN ('mensal','anual') AND dia_do_mes BETWEEN 1 AND 31) OR frequencia NOT IN ('mensal','anual')", name="ck_recurring_dia_mes"),
        CheckConstraint("(frequencia = 'semanal' AND dia_semana BETWEEN 0 AND 6) OR frequencia != 'semanal'", name="ck_recurring_dia_semana"),
        Index("ix_recurring_user_ativo_proxima", "user_id", "ativo", "proxima_execucao"),
    )