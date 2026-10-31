import json
import logging
import zoneinfo
from uuid import UUID
from datetime import datetime, timezone, time
from typing import Optional, Dict, Any, List
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.notification import Notification, NotificationPreference
from app.repositories.notification_repository import NotificationRepository
from app.alerts.insights import get_insight_provider
from app.core.config import settings
from app.core.exceptions import NotFoundError, AppError

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = NotificationRepository(db)

    async def get_or_create_preferences(self, user_id: UUID) -> NotificationPreference:
        prefs = await self.repo.get_preferences(user_id)
        if not prefs:
            prefs = await self.repo.create_default_preferences(user_id)
        return prefs

    async def update_preferences(self, user_id: UUID, data: dict) -> NotificationPreference:
        return await self.repo.upsert_preferences(user_id, data)

    def _is_quiet_hours(self, now_user: datetime, start_str: Optional[str], end_str: Optional[str]) -> bool:
        if not start_str or not end_str:
            return False

        try:
            sh, sm = map(int, start_str.split(":"))
            eh, em = map(int, end_str.split(":"))
            start_t = time(sh, sm)
            end_t = time(eh, em)
            curr_t = now_user.time()

            if start_t <= end_t:
                return start_t <= curr_t <= end_t
            else:  # Cruza a meia-noite (ex.: 22:00 até 07:00)
                return curr_t >= start_t or curr_t <= end_t
        except Exception:
            return False

    async def _count_notifications_today(self, user_id: UUID, user_tz_name: str) -> int:
        try:
            tz = zoneinfo.ZoneInfo(user_tz_name)
        except Exception:
            tz = timezone.utc

        now_user = datetime.now(tz)
        start_of_day_user = datetime(now_user.year, now_user.month, now_user.day, tzinfo=tz)
        start_of_day_utc = start_of_day_user.astimezone(timezone.utc)

        stmt = select(func.count()).select_from(Notification).where(
            Notification.user_id == user_id,
            Notification.created_at >= start_of_day_utc,
        )
        result = await self.db.execute(stmt)
        return int(result.scalar_one() or 0)

    def _matches_sensitivity(self, sensitivity: str, event_type: str, data: Dict[str, Any]) -> bool:
        level = data.get("level", 0)
        days_left = data.get("days_left", 99)

        if sensitivity == "low":
            # Apenas alertas críticos: overspending 100% ou parcela vencendo hoje
            if event_type == "overspending" and level >= 100:
                return True
            if event_type == "installment_due" and days_left == 0:
                return True
            return False

        elif sensitivity == "medium":
            # Overspending 80% e 100%, parcelas em até 3 dias, pico e comunicações
            if event_type == "overspending" and "level" in data and level < 80:
                return False
            if event_type == "installment_due" and "days_left" in data and days_left > 3:
                return False
            return True

        elif sensitivity == "high":
            # Todos os eventos
            return True

        return True

    async def processar_evento(
        self,
        user_id: UUID,
        event_type: str,
        data: Dict[str, Any],
        dedupe_key: Optional[str] = None,
        event_time: Optional[datetime] = None,
    ) -> Optional[Notification]:
        """
        Executa a esteira obrigatória de processamento de alertas:
        1. tipo habilitado
        2. sensibilidade
        3. quiet hours no fuso do usuário
        4. limite diário
        5. dedupe por (user_id, dedupe_key)
        6. geração de texto
        7. persistência
        8. push notification
        """
        # 1. Tipo habilitado
        prefs = await self.get_or_create_preferences(user_id)
        if event_type not in (prefs.enabled_types or []):
            return None

        # 2. Sensibilidade
        if not self._matches_sensitivity(prefs.sensitivity, event_type, data):
            return None

        # 3. Quiet hours no fuso do usuário
        try:
            tz = zoneinfo.ZoneInfo(prefs.timezone)
        except Exception:
            tz = timezone.utc

        now_user = (event_time or datetime.now(timezone.utc)).astimezone(tz)
        if self._is_quiet_hours(now_user, prefs.quiet_hours_start, prefs.quiet_hours_end):
            return None

        # 4. Limite diário
        count_today = await self._count_notifications_today(user_id, prefs.timezone)
        if count_today >= prefs.daily_limit:
            return None

        # 5. Dedupe por (user_id, dedupe_key)
        if dedupe_key:
            stmt_dedupe = select(Notification).where(
                Notification.user_id == user_id,
                Notification.dedupe_key == dedupe_key,
            )
            existing = (await self.db.execute(stmt_dedupe)).scalar_one_or_none()
            if existing:
                return None

        # 6. Geração de texto
        provider = get_insight_provider()
        title, body, payload = provider.generate_text(event_type, data)

        # Garantir URL relativa iniciando por /
        url = payload.get("url")
        if url:
            if not str(url).startswith("/"):
                payload["url"] = f"/{url}"
        else:
            payload["url"] = f"/notificacoes"

        # 7. Persistência
        notification = Notification(
            user_id=user_id,
            type=event_type,
            title=title,
            body=body,
            status="unread",
            payload=payload,
            dedupe_key=dedupe_key,
        )
        self.db.add(notification)
        await self.db.flush()
        await self.db.refresh(notification)

        # Atualiza a URL com o id gerado se aplicável
        if payload.get("url") == "/notificacoes":
            payload["url"] = f"/notificacoes/{str(notification.id)}"
            notification.payload = payload
            await self.db.flush()

        # 8. Push notification
        if prefs.channel_push and settings.VAPID_PRIVATE_KEY:
            await self._dispatch_push(user_id, notification)

        return notification

    async def _dispatch_push(self, user_id: UUID, notification: Notification) -> None:
        subscriptions = await self.repo.get_user_push_subscriptions(user_id)
        if not subscriptions:
            return

        payload = {
            "title": notification.title,
            "body": notification.body,
            "url": (notification.payload or {}).get("url", "/"),
            "tag": notification.dedupe_key or str(notification.id),
        }

        from pywebpush import webpush, WebPushException

        vapid_claims = {"sub": settings.VAPID_SUBJECT}

        for sub in subscriptions:
            sub_info = {
                "endpoint": sub.endpoint,
                "keys": {
                    "p256dh": sub.p256dh,
                    "auth": sub.auth,
                },
            }
            try:
                webpush(
                    subscription_info=sub_info,
                    data=json.dumps(payload),
                    vapid_private_key=settings.VAPID_PRIVATE_KEY,
                    vapid_claims=vapid_claims,
                )
            except WebPushException as ex:
                status_code = getattr(getattr(ex, "response", None), "status_code", None)
                if status_code in (404, 410):
                    logger.info(f"Removendo subscription expirada {sub.endpoint}")
                    await self.repo.delete_push_subscription_by_endpoint(sub.endpoint)
                else:
                    logger.warning(f"Erro ao enviar push notification para {sub.endpoint}: {ex}")
            except Exception as e:
                logger.warning(f"Erro inesperado no envio de push para {sub.endpoint}: {e}")

    async def list_notifications(
        self,
        user_id: UUID,
        status: Optional[str] = None,
        type_: Optional[str] = None,
        cursor: Optional[str] = None,
        limit: int = 20,
    ) -> tuple[List[Notification], Optional[str], int]:
        if limit < 1 or limit > 50:
            raise AppError("limit deve estar entre 1 e 50", "INVALID_LIMIT", status_code=422)

        items, next_cursor = await self.repo.get_notifications(
            user_id=user_id,
            status=status,
            type_=type_,
            cursor=cursor,
            limit=limit,
        )
        unread_count = await self.repo.count_unread(user_id)
        return items, next_cursor, unread_count

    async def read_notification(self, user_id: UUID, notification_id: UUID) -> None:
        notif = await self.repo.get_by_id(notification_id, user_id)
        if not notif:
            raise NotFoundError("Notificação não encontrada", "NOTIFICATION_NOT_FOUND")
        await self.repo.mark_as_read(notification_id, user_id)

    async def read_all_notifications(self, user_id: UUID) -> None:
        await self.repo.mark_all_as_read(user_id)

    async def record_feedback(self, user_id: UUID, notification_id: UUID, action: str) -> None:
        notif = await self.repo.get_by_id(notification_id, user_id)
        if not notif:
            raise NotFoundError("Notificação não encontrada", "NOTIFICATION_NOT_FOUND")

        await self.repo.record_feedback(notification_id, user_id, action)

        if action == "dismissed":
            notif.status = "dismissed"
            await self.db.flush()
        elif action == "opened":
            if notif.status == "unread":
                notif.status = "read"
                if not notif.read_at:
                    notif.read_at = datetime.now(timezone.utc)
                await self.db.flush()
