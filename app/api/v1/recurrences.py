from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from datetime import date
from app.db.session import get_db
from app.core.deps import get_current_user, PaginationParams
from app.schemas.recurrence import RecurrenceCreate, RecurrenceUpdate, RecurrenceResponse, RecurrenceGenerateResponse
from app.services.recurrence_service import RecurrenceService
from app.schemas.common import Page
from app.models.user import User


router = APIRouter(prefix="/recurrences", tags=["recurrences"])


@router.post("", response_model=RecurrenceResponse, status_code=status.HTTP_201_CREATED)
async def create_recurrence(data: RecurrenceCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = RecurrenceService(db)
    return await service.create(current_user.id, data)


@router.get("", response_model=Page[RecurrenceResponse])
async def list_recurrences(
    ativo_only: bool = True,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = RecurrenceService(db)
    recurrences, total = await service.list(current_user.id, ativo_only, pagination.page, pagination.size)
    return Page.create(recurrences, total, pagination.page, pagination.size)


@router.get("/{recurrence_id}", response_model=RecurrenceResponse)
async def get_recurrence(recurrence_id: UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = RecurrenceService(db)
    return await service.get(current_user.id, recurrence_id)


@router.patch("/{recurrence_id}", response_model=RecurrenceResponse)
async def update_recurrence(recurrence_id: UUID, data: RecurrenceUpdate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = RecurrenceService(db)
    return await service.update(current_user.id, recurrence_id, data)


@router.delete("/{recurrence_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recurrence(recurrence_id: UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = RecurrenceService(db)
    await service.delete(current_user.id, recurrence_id)


@router.post("/generate", response_model=RecurrenceGenerateResponse)
async def generate_all_pending(
    data_limite: date | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = RecurrenceService(db)
    return await service.generate_pending(current_user.id, data_limite)


@router.post("/{recurrence_id}/generate", response_model=RecurrenceGenerateResponse)
async def generate_by_id(
    recurrence_id: UUID,
    data_limite: date | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = RecurrenceService(db)
    return await service.generate_by_id(current_user.id, recurrence_id, data_limite)