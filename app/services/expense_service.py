import asyncio
import calendar
from collections import defaultdict
from uuid import UUID
from datetime import date as dt_date
from decimal import Decimal, ROUND_FLOOR, ROUND_HALF_UP
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.transaction import Transaction
from app.models.account import Account
from app.models.category import Category
from app.models.enums import TransactionType, TransactionStatus, AccountType, CategoryType
from app.schemas.expense import (
    ExpenseInstallmentResponse,
    ExpenseInstallmentCreate,
)
from app.core.exceptions import NotFoundError, AppError

# Lock de concorrência em memória por ID de despesa (garante atomicidade por processo)
_pay_locks: dict[UUID, asyncio.Lock] = defaultdict(asyncio.Lock)


def add_months(orig_date: dt_date, months: int) -> dt_date:
    """Adiciona meses a uma data tratando fim de mês e ano bissexto."""
    year = orig_date.year + (orig_date.month + months - 1) // 12
    month = (orig_date.month + months - 1) % 12 + 1
    max_days = calendar.monthrange(year, month)[1]
    day = min(orig_date.day, max_days)
    return dt_date(year, month, day)


def calculate_expense_metrics(
    total_amount: Decimal,
    installment_count: int,
    paid_installments: int,
    first_due_date: dt_date,
) -> dict:
    count = installment_count
    paid = paid_installments
    total = Decimal(str(total_amount))

    # installment_amount é total_amount / installment_count truncado em 2 casas decimais
    base_installment = (total / count).quantize(Decimal("0.01"), rounding=ROUND_FLOOR)
    
    # A diferença de centavos é somada à última parcela para que a soma seja exatamente total_amount
    last_installment = total - (base_installment * (count - 1))

    # Ao calcular paid_amount, considere as primeiras paid_installments com valor normal e última com ajuste
    if paid == count:
        paid_amount = total
    else:
        paid_amount = (base_installment * paid).quantize(Decimal("0.01"))

    remaining_amount = (total - paid_amount).quantize(Decimal("0.01"))
    remaining_installments = count - paid

    # progress_percent = round(paid_installments / installment_count * 100), como inteiro entre 0 e 100
    if count > 0:
        raw_pct = (Decimal(paid) / Decimal(count)) * Decimal("100")
        progress_percent = int(raw_pct.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    else:
        progress_percent = 0

    is_completed = (paid == count)

    if is_completed:
        next_due_date = None
    else:
        next_due_date = add_months(first_due_date, paid)

    return {
        "installment_amount": base_installment,
        "last_installment_amount": last_installment,
        "paid_amount": paid_amount,
        "remaining_amount": remaining_amount,
        "remaining_installments": remaining_installments,
        "progress_percent": progress_percent,
        "is_completed": is_completed,
        "next_due_date": next_due_date,
    }


class ExpenseService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _to_response(self, tx: Transaction) -> ExpenseInstallmentResponse:
        metrics = calculate_expense_metrics(
            total_amount=Decimal(str(tx.valor)),
            installment_count=tx.installment_count or 1,
            paid_installments=tx.paid_installments,
            first_due_date=tx.first_due_date or tx.data,
        )
        cat_name = tx.category_name or (tx.category.nome if tx.category else None)
        return ExpenseInstallmentResponse(
            id=tx.id,
            description=tx.descricao,
            category=cat_name,
            total_amount=Decimal(str(tx.valor)),
            installment_count=tx.installment_count or 1,
            installment_amount=metrics["installment_amount"],
            paid_installments=tx.paid_installments,
            remaining_installments=metrics["remaining_installments"],
            progress_percent=metrics["progress_percent"],
            paid_amount=metrics["paid_amount"],
            remaining_amount=metrics["remaining_amount"],
            first_due_date=tx.first_due_date or tx.data,
            next_due_date=metrics["next_due_date"],
            is_completed=metrics["is_completed"],
        )

    async def _get_or_create_default_account(self, user_id: UUID) -> Account:
        stmt = select(Account).where(Account.user_id == user_id, Account.ativo == True).limit(1)
        account = (await self.db.execute(stmt)).scalar_one_or_none()
        if not account:
            account = Account(
                user_id=user_id,
                nome="Conta Principal",
                tipo=AccountType.CORRENTE,
                saldo_inicial=0,
                moeda="BRL",
                ativo=True,
            )
            self.db.add(account)
            await self.db.flush()
            await self.db.refresh(account)
        return account

    async def list_installments(self, user_id: UUID, include_completed: bool = False) -> List[ExpenseInstallmentResponse]:
        stmt = select(Transaction).where(
            Transaction.user_id == user_id,
            Transaction.tipo == TransactionType.DESPESA,
            Transaction.is_installment == True,
        )
        if not include_completed:
            stmt = stmt.where(Transaction.paid_installments < Transaction.installment_count)

        stmt = stmt.order_by(Transaction.first_due_date.asc(), Transaction.criado_em.asc())
        result = await self.db.execute(stmt)
        transactions = result.scalars().all()

        return [self._to_response(tx) for tx in transactions]

    async def create_installment_expense(self, user_id: UUID, data: ExpenseInstallmentCreate) -> ExpenseInstallmentResponse:
        account = await self._get_or_create_default_account(user_id)

        categoria_id = None
        if data.category:
            stmt_cat = select(Category).where(
                Category.user_id == user_id,
                Category.nome.ilike(data.category),
            ).limit(1)
            cat = (await self.db.execute(stmt_cat)).scalar_one_or_none()
            if cat:
                categoria_id = cat.id

        tx = Transaction(
            user_id=user_id,
            conta_id=account.id,
            categoria_id=categoria_id,
            tipo=TransactionType.DESPESA,
            valor=data.total_amount,
            descricao=data.description,
            category_name=data.category,
            data=data.first_due_date,
            first_due_date=data.first_due_date,
            is_installment=True,
            installment_count=data.installment_count,
            paid_installments=0,
            status=TransactionStatus.CONFIRMADO,
        )
        self.db.add(tx)
        await self.db.flush()
        await self.db.refresh(tx)
        return self._to_response(tx)

    async def pay_installment(self, user_id: UUID, expense_id: UUID) -> ExpenseInstallmentResponse:
        async with _pay_locks[expense_id]:
            stmt = select(Transaction).where(Transaction.id == expense_id, Transaction.user_id == user_id)
            
            # Lock pessimista quando suportado pelo dialeto (PostgreSQL)
            bind = self.db.get_bind()
            if bind and bind.dialect.name != "sqlite":
                stmt = stmt.with_for_update()

            result = await self.db.execute(stmt)
            tx = result.scalar_one_or_none()

            if not tx:
                raise NotFoundError("Despesa não encontrada", "EXPENSE_NOT_FOUND")

            if not tx.is_installment:
                raise AppError("Esta despesa não é parcelada", "NOT_INSTALLMENT_TRANSACTION", status_code=422)

            count = tx.installment_count or 0
            if tx.paid_installments >= count:
                raise AppError("Esta despesa já foi quitada", "INSTALLMENT_ALREADY_COMPLETED", status_code=409)

            tx.paid_installments += 1
            await self.db.flush()
            await self.db.refresh(tx)
            return self._to_response(tx)

    async def update_paid_installments(self, user_id: UUID, expense_id: UUID, paid_installments: int) -> ExpenseInstallmentResponse:
        stmt = select(Transaction).where(Transaction.id == expense_id, Transaction.user_id == user_id)
        result = await self.db.execute(stmt)
        tx = result.scalar_one_or_none()

        if not tx:
            raise NotFoundError("Despesa não encontrada", "EXPENSE_NOT_FOUND")

        if not tx.is_installment:
            raise AppError("Esta despesa não é parcelada", "NOT_INSTALLMENT_TRANSACTION", status_code=422)

        count = tx.installment_count or 0
        if paid_installments < 0 or paid_installments > count:
            raise AppError(
                f"paid_installments deve estar entre 0 e {count}",
                "INVALID_PAID_INSTALLMENTS",
                status_code=422,
            )

        tx.paid_installments = paid_installments
        await self.db.flush()
        await self.db.refresh(tx)
        return self._to_response(tx)
