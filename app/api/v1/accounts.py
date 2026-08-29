from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.db.session import get_db
from app.core.deps import get_current_user, PaginationParams
from app.schemas.account import AccountCreate, AccountUpdate, AccountResponse, AccountWithBalance
from app.services.account_service import AccountService
from app.schemas.common import Page
from app.models.user import User


router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.post("", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(data: AccountCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = AccountService(db)
    return await service.create(current_user.id, data)


@router.get("", response_model=Page[AccountResponse])
async def list_accounts(pagination: PaginationParams = Depends(), db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = AccountService(db)
    accounts, total = await service.list(current_user.id, pagination.page, pagination.size)
    return Page.create(accounts, total, pagination.page, pagination.size)


@router.get("/{account_id}", response_model=AccountResponse)
async def get_account(account_id: UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = AccountService(db)
    return await service.get(current_user.id, account_id)


@router.get("/{account_id}/balance", response_model=AccountWithBalance)
async def get_account_balance(account_id: UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = AccountService(db)
    account = await service.get(current_user.id, account_id)
    return account


@router.patch("/{account_id}", response_model=AccountResponse)
async def update_account(account_id: UUID, data: AccountUpdate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = AccountService(db)
    return await service.update(current_user.id, account_id, data)


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(account_id: UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = AccountService(db)
    soft_deleted = await service.delete(current_user.id, account_id)
    return