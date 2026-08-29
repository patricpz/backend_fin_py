from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional
from app.db.session import get_db
from app.core.deps import get_current_user, PaginationParams
from app.schemas.category import CategoryCreate, CategoryUpdate, CategoryResponse, CategoryTree
from app.services.category_service import CategoryService
from app.schemas.common import Page
from app.models.user import User


router = APIRouter(prefix="/categories", tags=["categories"])


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(data: CategoryCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = CategoryService(db)
    return await service.create(current_user.id, data)


@router.get("", response_model=Page[CategoryResponse])
async def list_categories(
    tipo: Optional[str] = None,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = CategoryService(db)
    categories, total = await service.list(current_user.id, tipo, pagination.page, pagination.size)
    return Page.create(categories, total, pagination.page, pagination.size)


@router.get("/tree", response_model=list[CategoryTree])
async def get_categories_tree(tipo: Optional[str] = None, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = CategoryService(db)
    return await service.get_tree(current_user.id, tipo)


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(category_id: UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = CategoryService(db)
    return await service.get(current_user.id, category_id)


@router.patch("/{category_id}", response_model=CategoryResponse)
async def update_category(category_id: UUID, data: CategoryUpdate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = CategoryService(db)
    return await service.update(current_user.id, category_id, data)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(category_id: UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = CategoryService(db)
    soft_deleted = await service.delete(current_user.id, category_id)
    return