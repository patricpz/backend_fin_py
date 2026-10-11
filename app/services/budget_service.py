from __future__ import annotations

from uuid import UUID
from datetime import date
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.budget import Budget
from app.models.category import Category
from app.models.transaction import Transaction
from app.repositories.budget_repository import BudgetRepository
from app.repositories.category_repository import CategoryRepository
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.budget import BudgetCreate, BudgetUpdate, BudgetProgress
from app.core.exceptions import NotFoundError, BusinessRuleError, ConflictError
from app.models.enums import CategoryType, TransactionType, TransactionStatus


class BudgetService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = BudgetRepository(db)
        self.cat_repo = CategoryRepository(db)
        self.tx_repo = TransactionRepository(db)

    async def _validate_category(self, user_id: UUID, categoria_id: UUID) -> Category:
        category = await self.cat_repo.get_by_id(categoria_id, user_id)
        if not category:
            raise NotFoundError("Categoria não encontrada", "CATEGORY_NOT_FOUND")
        if not category.ativo:
            raise BusinessRuleError("Categoria inativa", "CATEGORY_INACTIVE")
        if category.tipo != CategoryType.DESPESA:
            raise BusinessRuleError("Orçamentos só podem ser criados para categorias de despesa", "BUDGET_INVALID_CATEGORY_TYPE")
        return category

    async def create(self, user_id: UUID, data: BudgetCreate) -> Budget:
        await self._validate_category(user_id, data.categoria_id)

        existing = await self.repo.get_by_categoria_periodo(user_id, data.categoria_id, data.mes, data.ano)
        if existing:
            raise ConflictError("Já existe orçamento para esta categoria no período", "BUDGET_EXISTS")

        budget = Budget(user_id=user_id, **data.model_dump())
        self.db.add(budget)
        await self.db.flush()
        await self.db.refresh(budget)
        return budget

    async def get(self, user_id: UUID, budget_id: UUID) -> Budget:
        budget = await self.repo.get_by_id(budget_id, user_id)
        if not budget:
            raise NotFoundError("Orçamento não encontrado", "BUDGET_NOT_FOUND")
        return budget

    async def list(self, user_id: UUID, mes: int | None = None, ano: int | None = None, page: int = 1, size: int = 20):
        budgets = await self.repo.get_by_user(user_id, mes, ano, size, (page - 1) * size)
        total = await self.repo.count_by_user(user_id, mes, ano)
        return budgets, total

    async def update(self, user_id: UUID, budget_id: UUID, data: BudgetUpdate) -> Budget:
        budget = await self.get(user_id, budget_id)
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(budget, field, value)
        await self.db.flush()
        await self.db.refresh(budget)
        return budget

    async def delete(self, user_id: UUID, budget_id: UUID) -> None:
        budget = await self.get(user_id, budget_id)
        await self.repo.delete(budget)

    async def get_progress(self, user_id: UUID, budget_id: UUID) -> BudgetProgress:
        budget = await self.get(user_id, budget_id)

        data_inicio = date(budget.ano, budget.mes, 1)
        if budget.mes == 12:
            data_fim = date(budget.ano + 1, 1, 1)
        else:
            data_fim = date(budget.ano, budget.mes + 1, 1)

        from app.repositories.category_repository import CategoryRepository
        cat_repo = CategoryRepository(self.db)
        subcategories = await cat_repo.get_by_user(budget.user_id, tipo=None, ativo_only=True, limit=1000, offset=0)
        sub_ids = [budget.categoria_id] + [c.id for c in subcategories if c.categoria_pai_id == budget.categoria_id]

        valor_gasto = Decimal("0")
        for sub_id in sub_ids:
            gasto = await self.tx_repo.get_category_spending(budget.user_id, sub_id, data_inicio, data_fim)
            valor_gasto += gasto

        percentual = float(valor_gasto / budget.valor_limite * 100) if budget.valor_limite > 0 else 0
        alerta = percentual >= budget.alerta_percentual

        return BudgetProgress(
            budget_id=budget.id,
            categoria_id=budget.categoria_id,
            categoria_nome=budget.category.nome,
            valor_limite=budget.valor_limite,
            valor_gasto=valor_gasto,
            percentual=percentual,
            alerta=alerta,
            mes=budget.mes,
            ano=budget.ano,
        )