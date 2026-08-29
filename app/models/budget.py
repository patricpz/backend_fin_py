import uuid
from sqlalchemy import String, Numeric, SmallInteger, ForeignKey, Index, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin, GUID
from app.models.enums import BudgetAlertPercent


class Budget(Base, TimestampMixin):
    __tablename__ = "budgets"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    categoria_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False)
    valor_limite: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    mes: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    ano: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    alerta_percentual: Mapped[int] = mapped_column(SmallInteger, default=BudgetAlertPercent.DEFAULT, nullable=False)

    user = relationship("User", back_populates="budgets")
    category = relationship("Category", back_populates="budgets")

    __table_args__ = (
        CheckConstraint("valor_limite >= 0", name="ck_budgets_valor_limite_nonneg"),
        CheckConstraint("mes BETWEEN 1 AND 12", name="ck_budgets_mes_valid"),
        CheckConstraint("ano >= 2000", name="ck_budgets_ano_valid"),
        CheckConstraint("alerta_percentual BETWEEN 1 AND 100", name="ck_budgets_alerta_percent"),
        UniqueConstraint("user_id", "categoria_id", "mes", "ano", name="uq_budget_user_cat_period"),
        Index("ix_budgets_user_period", "user_id", "ano", "mes"),
    )