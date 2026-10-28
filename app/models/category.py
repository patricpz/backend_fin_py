import uuid
from sqlalchemy import String, Boolean, Index, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin, GUID
from app.models.enums import CategoryType


class Category(Base, TimestampMixin):
    __tablename__ = "categories"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    categoria_pai_id: Mapped[uuid.UUID | None] = mapped_column(GUID, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    tipo: Mapped[CategoryType] = mapped_column(String(20), nullable=False)
    cor: Mapped[str] = mapped_column(String(30), nullable=False, default="#6B7280")
    icone: Mapped[str] = mapped_column(String(60), nullable=False, default="Tag")
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user = relationship("User", back_populates="categories")
    parent = relationship("Category", remote_side="Category.id", back_populates="children")
    children = relationship("Category", back_populates="parent")
    transactions = relationship("Transaction", back_populates="category")
    budgets = relationship("Budget", back_populates="category")

    __table_args__ = (
        Index("ix_categories_user_tipo_ativo", "user_id", "tipo", "ativo"),
        Index("ix_categories_user_nome_tipo", "user_id", "nome", "tipo", unique=True),
    )
