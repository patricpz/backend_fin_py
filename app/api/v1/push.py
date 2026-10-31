from fastapi import APIRouter, Depends, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.db.session import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.push import (
    PushPublicKeyResponse,
    PushSubscriptionRequest,
    PushSubscriptionResponse,
)
from app.repositories.notification_repository import NotificationRepository
from app.core.config import settings
from app.core.exceptions import AppError, NotFoundError

router = APIRouter(prefix="/push", tags=["push"])


@router.get("/public-key", response_model=PushPublicKeyResponse)
async def get_vapid_public_key():
    if not settings.VAPID_PUBLIC_KEY:
        raise AppError("Web Push não está configurado neste servidor", "PUSH_NOT_CONFIGURED", status_code=503)
    return PushPublicKeyResponse(public_key=settings.VAPID_PUBLIC_KEY)


@router.post("/subscriptions", response_model=PushSubscriptionResponse)
async def create_or_update_push_subscription(
    data: PushSubscriptionRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = NotificationRepository(db)
    sub, is_new = await repo.upsert_push_subscription(
        user_id=current_user.id,
        endpoint=data.endpoint,
        p256dh=data.p256dh,
        auth=data.auth,
        user_agent=data.user_agent,
    )
    if is_new:
        response.status_code = status.HTTP_201_CREATED
    else:
        response.status_code = status.HTTP_200_OK

    return PushSubscriptionResponse(id=sub.id)


@router.delete("/subscriptions/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_push_subscription(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = NotificationRepository(db)
    deleted = await repo.delete_push_subscription(id, current_user.id)
    if not deleted:
        raise NotFoundError("Inscrição de push não encontrada", "PUSH_SUBSCRIPTION_NOT_FOUND")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
