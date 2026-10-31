import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    String,
    Text,
    Boolean,
    Integer,
    ForeignKey,
    Index,
    DateTime,
    JSON,
    func,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, GUID


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="unread", nullable=False)
    payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    dedupe_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
    read_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user = relationship("User")

    __table_args__ = (
        Index("ix_notifications_user_status", "user_id", "status"),
        Index("ix_notifications_user_created_at_id", "user_id", "created_at", "id"),
        UniqueConstraint("user_id", "dedupe_key", name="uq_notifications_user_dedupe"),
    )


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    enabled_types: Mapped[List[str]] = mapped_column(
        JSON,
        default=lambda: ["overspending", "spending_spike", "installment_due", "tip", "summary"],
        nullable=False,
    )
    channel_in_app: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    channel_push: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sensitivity: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)
    quiet_hours_start: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)
    quiet_hours_end: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)
    timezone: Mapped[str] = mapped_column(String(50), default="America/Fortaleza", nullable=False)
    daily_limit: Mapped[int] = mapped_column(Integer, default=3, nullable=False)

    user = relationship("User")


class PushSubscription(Base):
    __tablename__ = "push_subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    endpoint: Mapped[str] = mapped_column(Text, unique=True, nullable=False, index=True)
    p256dh: Mapped[str] = mapped_column(Text, nullable=False)
    auth: Mapped[str] = mapped_column(Text, nullable=False)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    user = relationship("User")


class NotificationFeedback(Base):
    __tablename__ = "notification_feedback"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    notification_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("notifications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    notification = relationship("Notification")
    user = relationship("User")
