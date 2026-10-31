import base64
from typing import Optional, List, Tuple
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy import select, func, and_, or_, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.notification import (
    Notification,
    NotificationPreference,
    PushSubscription,
    NotificationFeedback,
)
from app.core.exceptions import AppError


class NotificationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    def encode_cursor(self, created_at: datetime, item_id: UUID) -> str:
        raw = f"{created_at.isoformat()}|{str(item_id)}"
        return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("utf-8")

    def decode_cursor(self, cursor_str: str) -> Tuple[datetime, UUID]:
        try:
            raw = base64.urlsafe_b64decode(cursor_str.encode("utf-8")).decode("utf-8")
            parts = raw.split("|")
            if len(parts) != 2:
                raise ValueError("Cursor inválido")
            dt = datetime.fromisoformat(parts[0])
            uid = UUID(parts[1])
            return dt, uid
        except Exception:
            raise AppError("Cursor inválido", "INVALID_CURSOR", status_code=400)

    async def get_notifications(
        self,
        user_id: UUID,
        status: Optional[str] = None,
        type_: Optional[str] = None,
        cursor: Optional[str] = None,
        limit: int = 20,
    ) -> Tuple[List[Notification], Optional[str]]:
        stmt = select(Notification).where(Notification.user_id == user_id)

        if status:
            stmt = stmt.where(Notification.status == status)
        if type_:
            stmt = stmt.where(Notification.type == type_)

        if cursor:
            cursor_dt, cursor_id = self.decode_cursor(cursor)
            stmt = stmt.where(
                or_(
                    Notification.created_at < cursor_dt,
                    and_(
                        Notification.created_at == cursor_dt,
                        Notification.id < cursor_id,
                    ),
                )
            )

        stmt = stmt.order_by(Notification.created_at.desc(), Notification.id.desc()).limit(limit + 1)
        result = await self.db.execute(stmt)
        rows = list(result.scalars().all())

        next_cursor = None
        if len(rows) > limit:
            items = rows[:limit]
            last_item = items[-1]
            next_cursor = self.encode_cursor(last_item.created_at, last_item.id)
        else:
            items = rows

        return items, next_cursor

    async def count_unread(self, user_id: UUID) -> int:
        stmt = select(func.count()).select_from(Notification).where(
            Notification.user_id == user_id,
            Notification.status == "unread",
        )
        result = await self.db.execute(stmt)
        return int(result.scalar_one() or 0)

    async def get_by_id(self, notification_id: UUID, user_id: UUID) -> Optional[Notification]:
        stmt = select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def mark_as_read(self, notification_id: UUID, user_id: UUID) -> bool:
        """Marca como read e preenche read_at. Idempotente. Retorna True se encontrado."""
        notif = await self.get_by_id(notification_id, user_id)
        if not notif:
            return False

        if notif.status != "read":
            notif.status = "read"
            if not notif.read_at:
                notif.read_at = datetime.now(timezone.utc)
            await self.db.flush()
        return True

    async def mark_all_as_read(self, user_id: UUID) -> None:
        stmt = (
            update(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.status == "unread",
            )
            .values(
                status="read",
                read_at=datetime.now(timezone.utc),
            )
        )
        await self.db.execute(stmt)
        await self.db.flush()

    async def record_feedback(self, notification_id: UUID, user_id: UUID, action: str) -> None:
        feedback = NotificationFeedback(
            notification_id=notification_id,
            user_id=user_id,
            action=action,
        )
        self.db.add(feedback)
        await self.db.flush()

    async def get_preferences(self, user_id: UUID) -> Optional[NotificationPreference]:
        stmt = select(NotificationPreference).where(NotificationPreference.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_default_preferences(self, user_id: UUID) -> NotificationPreference:
        prefs = NotificationPreference(
            user_id=user_id,
            enabled_types=["overspending", "spending_spike", "installment_due", "tip", "summary"],
            channel_in_app=True,
            channel_push=False,
            sensitivity="medium",
            quiet_hours_start=None,
            quiet_hours_end=None,
            timezone="America/Fortaleza",
            daily_limit=3,
        )
        self.db.add(prefs)
        await self.db.flush()
        await self.db.refresh(prefs)
        return prefs

    async def upsert_preferences(self, user_id: UUID, data: dict) -> NotificationPreference:
        prefs = await self.get_preferences(user_id)
        if not prefs:
            prefs = NotificationPreference(user_id=user_id, **data)
            self.db.add(prefs)
        else:
            for k, v in data.items():
                setattr(prefs, k, v)
        await self.db.flush()
        await self.db.refresh(prefs)
        return prefs

    async def get_push_subscription_by_endpoint(self, endpoint: str) -> Optional[PushSubscription]:
        stmt = select(PushSubscription).where(PushSubscription.endpoint == endpoint)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_push_subscription_by_id(self, subscription_id: UUID, user_id: UUID) -> Optional[PushSubscription]:
        stmt = select(PushSubscription).where(
            PushSubscription.id == subscription_id,
            PushSubscription.user_id == user_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_push_subscription(
        self, user_id: UUID, endpoint: str, p256dh: str, auth: str, user_agent: Optional[str] = None
    ) -> Tuple[PushSubscription, bool]:
        """Retorna (subscription, is_new)."""
        existing = await self.get_push_subscription_by_endpoint(endpoint)
        if existing:
            existing.user_id = user_id
            existing.p256dh = p256dh
            existing.auth = auth
            existing.user_agent = user_agent
            await self.db.flush()
            await self.db.refresh(existing)
            return existing, False
        else:
            new_sub = PushSubscription(
                user_id=user_id,
                endpoint=endpoint,
                p256dh=p256dh,
                auth=auth,
                user_agent=user_agent,
            )
            self.db.add(new_sub)
            await self.db.flush()
            await self.db.refresh(new_sub)
            return new_sub, True

    async def delete_push_subscription(self, subscription_id: UUID, user_id: UUID) -> bool:
        sub = await self.get_push_subscription_by_id(subscription_id, user_id)
        if not sub:
            return False
        await self.db.delete(sub)
        await self.db.flush()
        return True

    async def get_user_push_subscriptions(self, user_id: UUID) -> List[PushSubscription]:
        stmt = select(PushSubscription).where(PushSubscription.user_id == user_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def delete_push_subscription_by_endpoint(self, endpoint: str) -> None:
        stmt = delete(PushSubscription).where(PushSubscription.endpoint == endpoint)
        await self.db.execute(stmt)
        await self.db.flush()
