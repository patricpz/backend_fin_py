import uuid
from datetime import date
from sqlalchemy import String, Numeric, Date, ForeignKey, Index, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin, GUID
from app.models.enums import GoalStatus, GoalContributionType


class Goal(Base, TimestampMixin):
    __tablename__ = "goals"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    descricao: Mapped[str | None] = mapped_column(String(500), nullable=True)
    valor_alvo: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    data_alvo: Mapped[date | None] = mapped_column(Date, nullable=True)
    categoria: Mapped[str | None] = mapped_column(String(80), nullable=True)
    status: Mapped[GoalStatus] = mapped_column(String(20), default=GoalStatus.EM_ANDAMENTO, nullable=False)

    user = relationship("User", back_populates="goals")
    contributions = relationship("GoalContribution", back_populates="goal", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("valor_alvo > 0", name="ck_goals_valor_alvo_positive"),
        Index("ix_goals_user_status", "user_id", "status"),
    )


class GoalContribution(Base, TimestampMixin):
    __tablename__ = "goal_contributions"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    goal_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("goals.id", ondelete="CASCADE"), nullable=False, index=True)
    valor: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    tipo: Mapped[GoalContributionType] = mapped_column(String(20), nullable=False)
    data: Mapped[date] = mapped_column(Date, nullable=False)
    observacao: Mapped[str | None] = mapped_column(String(200), nullable=True)

    goal = relationship("Goal", back_populates="contributions")

    __table_args__ = (
        CheckConstraint("valor > 0", name="ck_goal_contrib_valor_positive"),
        Index("ix_goal_contrib_goal_data", "goal_id", "data"),
    )