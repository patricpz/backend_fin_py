from __future__ import annotations

from uuid import UUID
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.account import Account
from app.repositories.account_repository import AccountRepository
from app.schemas.account import AccountCreate, AccountUpdate
from app.core.exceptions import NotFoundError, BusinessRuleError


class AccountService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AccountRepository(db)

    @staticmethod
    def _money(value) -> Decimal:
        return Decimal(str(value)).quantize(Decimal("0.01"))

    async def _with_balance(self, account: Account) -> Account:
        from app.repositories.transaction_repository import TransactionRepository
        tx_repo = TransactionRepository(self.db)
        balance = await tx_repo.get_account_balance(account.id)
        account.saldo_atual = self._money(Decimal(account.saldo_inicial) + Decimal(balance))
        return account

    async def create(self, user_id: UUID, data: AccountCreate) -> Account:
        account = Account(user_id=user_id, **data.model_dump())
        self.db.add(account)
        await self.db.flush()
        await self.db.refresh(account)
        account.saldo_atual = self._money(account.saldo_inicial)
        return account

    async def get(self, user_id: UUID, account_id: UUID) -> Account:
        account = await self.repo.get_by_id(account_id, user_id)
        if not account:
            raise NotFoundError("Conta não encontrada", "ACCOUNT_NOT_FOUND")
        return await self._with_balance(account)

    async def list(self, user_id: UUID, page: int = 1, size: int = 20, ativo_only: bool = True):
        accounts = await self.repo.get_by_user(user_id, ativo_only, size, (page - 1) * size)
        total = await self.repo.count_by_user(user_id, ativo_only)
        accounts = [await self._with_balance(acc) for acc in accounts]
        return accounts, total

    async def update(self, user_id: UUID, account_id: UUID, data: AccountUpdate) -> Account:
        account = await self.repo.get_by_id(account_id, user_id)
        if not account:
            raise NotFoundError("Conta não encontrada", "ACCOUNT_NOT_FOUND")
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(account, field, value)
        await self.db.flush()
        await self.db.refresh(account)
        return await self._with_balance(account)

    async def delete(self, user_id: UUID, account_id: UUID) -> bool:
        account = await self.get(user_id, account_id)
        has_transactions = await self.repo.has_transactions(account_id)
        if has_transactions:
            account.ativo = False
            await self.db.flush()
            return False
        else:
            await self.repo.delete(account)
            return True

    async def get_balance(self, user_id: UUID, account_id: UUID) -> float:
        account = await self.repo.get_by_id(account_id, user_id)
        if not account:
            raise NotFoundError("Conta não encontrada", "ACCOUNT_NOT_FOUND")
        from app.repositories.transaction_repository import TransactionRepository
        tx_repo = TransactionRepository(self.db)
        balance = await tx_repo.get_account_balance(account_id)
        return float(account.saldo_inicial) + float(balance)