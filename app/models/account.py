import uuid
from sqlalchemy import String, Numeric, Boolean, CheckConstraint, Index, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin, GUID
from app.models.enums import AccountType


class Account(Base, TimestampMixin):
    __tablename__ = "accounts"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    tipo: Mapped[AccountType] = mapped_column(String(20), nullable=False)
    saldo_inicial: Mapped[float] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    moeda: Mapped[str] = mapped_column(String(3), default="BRL", nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user = relationship("User", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="account", foreign_keys="Transaction.conta_id")
    transactions_destino = relationship("Transaction", back_populates="account_destino", foreign_keys="Transaction.conta_destino_id")
    recurrences = relationship("RecurringTransaction", back_populates="account", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("saldo_inicial >= 0", name="ck_accounts_saldo_inicial_nonneg"),
        Index("ix_accounts_user_ativo", "user_id", "ativo"),
    )