from uuid import UUID
from datetime import date
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.models.transaction import Transaction
from app.models.account import Account
from app.models.category import Category
from app.repositories.transaction_repository import TransactionRepository
from app.repositories.account_repository import AccountRepository
from app.repositories.category_repository import CategoryRepository
from app.schemas.transaction import TransactionCreate, TransactionUpdate, TransactionFilters
from app.core.exceptions import NotFoundError, BusinessRuleError
from app.models.enums import TransactionType, TransactionStatus


class TransactionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.tx_repo = TransactionRepository(db)
        self.account_repo = AccountRepository(db)
        self.category_repo = CategoryRepository(db)

    async def _validate_account(self, user_id: UUID, account_id: UUID) -> Account:
        account = await self.account_repo.get_by_id(account_id, user_id)
        if not account:
            raise NotFoundError("Conta não encontrada", "ACCOUNT_NOT_FOUND")
        if not account.ativo:
            raise BusinessRuleError("Conta inativa", "ACCOUNT_INACTIVE")
        return account

    async def _validate_category(self, user_id: UUID, category_id: UUID, expected_tipo: str | None = None) -> Category:
        category = await self.category_repo.get_by_id(category_id, user_id)
        if not category:
            raise NotFoundError("Categoria não encontrada", "CATEGORY_NOT_FOUND")
        if not category.ativo:
            raise BusinessRuleError("Categoria inativa", "CATEGORY_INACTIVE")
        if expected_tipo and category.tipo != expected_tipo:
            raise BusinessRuleError(f"Categoria deve ser do tipo {expected_tipo}", "INVALID_CATEGORY_TYPE")
        return category

    async def _validate_transfer(self, user_id: UUID, conta_id: UUID, conta_destino_id: UUID) -> tuple[Account, Account]:
        if conta_id == conta_destino_id:
            raise BusinessRuleError("Conta de origem e destino devem ser diferentes", "SAME_ACCOUNT_TRANSFER")
        conta_origem = await self._validate_account(user_id, conta_id)
        conta_destino = await self._validate_account(user_id, conta_destino_id)
        return conta_origem, conta_destino

    async def create(self, user_id: UUID, data: TransactionCreate) -> Transaction:
        if data.idempotency_key:
            existing = await self.tx_repo.get_by_idempotency_key(user_id, data.idempotency_key)
            if existing:
                return existing

        if data.tipo == TransactionType.TRANSFERENCIA:
            await self._validate_transfer(user_id, data.conta_id, data.conta_destino_id)
            if data.categoria_id:
                raise BusinessRuleError("Transferências não devem ter categoria", "TRANSFER_NO_CATEGORY")
        elif data.tipo == TransactionType.RECEITA:
            await self._validate_account(user_id, data.conta_id)
            await self._validate_category(user_id, data.categoria_id, TransactionType.RECEITA)
        elif data.tipo == TransactionType.DESPESA:
            await self._validate_account(user_id, data.conta_id)
            await self._validate_category(user_id, data.categoria_id, TransactionType.DESPESA)

        transaction = Transaction(user_id=user_id, **data.model_dump())
        self.db.add(transaction)
        await self.db.flush()
        await self.db.refresh(transaction)
        return transaction

    async def get(self, user_id: UUID, transaction_id: UUID) -> Transaction:
        transaction = await self.tx_repo.get_by_id(transaction_id, user_id)
        if not transaction:
            raise NotFoundError("Transação não encontrada", "TRANSACTION_NOT_FOUND")
        return transaction

    async def list(self, user_id: UUID, filters: TransactionFilters | None, page: int = 1, size: int = 20):
        transactions = await self.tx_repo.get_by_user(user_id, filters, size, (page - 1) * size)
        total = await self.tx_repo.count_by_user(user_id, filters)
        return transactions, total

    async def update(self, user_id: UUID, transaction_id: UUID, data: TransactionUpdate) -> Transaction:
        transaction = await self.get(user_id, transaction_id)
        update_data = data.model_dump(exclude_unset=True)

        if "tipo" in update_data or "conta_id" in update_data or "conta_destino_id" in update_data or "categoria_id" in update_data:
            tipo = update_data.get("tipo", transaction.tipo)
            conta_id = update_data.get("conta_id", transaction.conta_id)
            conta_destino_id = update_data.get("conta_destino_id", transaction.conta_destino_id)
            categoria_id = update_data.get("categoria_id", transaction.categoria_id)

            if tipo == TransactionType.TRANSFERENCIA:
                await self._validate_transfer(user_id, conta_id, conta_destino_id)
                if categoria_id:
                    raise BusinessRuleError("Transferências não devem ter categoria", "TRANSFER_NO_CATEGORY")
            elif tipo == TransactionType.RECEITA:
                await self._validate_account(user_id, conta_id)
                await self._validate_category(user_id, categoria_id, TransactionType.RECEITA)
            elif tipo == TransactionType.DESPESA:
                await self._validate_account(user_id, conta_id)
                await self._validate_category(user_id, categoria_id, TransactionType.DESPESA)

        for field, value in update_data.items():
            setattr(transaction, field, value)

        await self.db.flush()
        await self.db.refresh(transaction)
        return transaction

    async def delete(self, user_id: UUID, transaction_id: UUID) -> None:
        transaction = await self.get(user_id, transaction_id)
        await self.tx_repo.delete(transaction)

    async def confirm(self, user_id: UUID, transaction_id: UUID) -> Transaction:
        transaction = await self.get(user_id, transaction_id)
        if transaction.status == TransactionStatus.CONFIRMADO:
            return transaction
        transaction.status = TransactionStatus.CONFIRMADO
        await self.db.flush()
        await self.db.refresh(transaction)
        return transaction