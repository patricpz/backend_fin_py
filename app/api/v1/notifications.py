from fastapi import APIRouter, Depends, status, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional, Literal
from app.db.session import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.notification import (
    NotificationListResponse,
    NotificationResponse,
    NotificationFeedbackRequest,
    NotificationPreferenceResponse,
    NotificationPreferenceUpdate,
)
from app.services.notification_service import NotificationService
from app.core.config import settings
from app.core.exceptions import AppError

router = APIRouter(tags=["notifications"])


@router.get("/notifications", response_model=NotificationListResponse)
async def list_notifications(
    status: Optional[Literal["unread", "read", "dismissed"]] = None,
    type: Optional[Literal["overspending", "spending_spike", "installment_due", "tip", "summary"]] = None,
    cursor: Optional[str] = None,
    limit: int = Query(default=20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = NotificationService(db)
    items, next_cursor, unread_count = await service.list_notifications(
        user_id=current_user.id,
        status=status,
        type_=type,
        cursor=cursor,
        limit=limit,
    )
    return NotificationListResponse(
        items=[NotificationResponse.model_validate(n) for n in items],
        next_cursor=next_cursor,
        unread_count=unread_count,
    )


@router.patch("/notifications/{id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_notification_as_read(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = NotificationService(db)
    await service.read_notification(current_user.id, id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/notifications/read-all", status_code=status.HTTP_204_NO_CONTENT)
async def mark_all_notifications_as_read(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = NotificationService(db)
    await service.read_all_notifications(current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/notifications/{id}/feedback", status_code=status.HTTP_204_NO_CONTENT)
async def submit_notification_feedback(
    id: UUID,
    data: NotificationFeedbackRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = NotificationService(db)
    await service.record_feedback(current_user.id, id, data.action)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/notification-preferences", response_model=NotificationPreferenceResponse)
async def get_notification_preferences(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = NotificationService(db)
    prefs = await service.get_or_create_preferences(current_user.id)
    return NotificationPreferenceResponse.model_validate(prefs)


@router.put("/notification-preferences", response_model=NotificationPreferenceResponse)
async def update_notification_preferences(
    data: NotificationPreferenceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = NotificationService(db)
    prefs = await service.update_preferences(current_user.id, data.model_dump())
    return NotificationPreferenceResponse.model_validate(prefs)


@router.post("/notifications/test", status_code=status.HTTP_200_OK)
async def create_test_notification(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if settings.APP_ENV != "development":
        # Em outros ambientes, retorna 404, não 403, para não revelar que a rota existe
        raise AppError("Not Found", "NOT_FOUND", status_code=404)

    service = NotificationService(db)
    notif = await service.processar_evento(
        user_id=current_user.id,
        event_type="overspending",
        data={
            "category": "Alimentação",
            "orcado": 1000.0,
            "gasto": 1180.0,
            "level": 100,
            "percentual": 118.0,
            "url": "/notificacoes/teste",
        },
        dedupe_key=None,
    )
    return {"message": "Notificação de teste processada com sucesso", "notification_id": str(notif.id) if notif else None}
