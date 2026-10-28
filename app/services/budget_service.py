from __future__ import annotations

from uuid import UUID
from datetime import date
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.budget import Budget
from app.models.category import Category
from app.repositories.budget_repository import BudgetRepository
from app.repositories.category_repository import CategoryRepository
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.budget import BudgetCreate, BudgetUpdate, BudgetResponse, BudgetProgress
from app.core.exceptions import NotFoundError, BusinessRuleError, ConflictError
from app.models.enums import CategoryType


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

    async def _calculate_spent(self, user_id: UUID, categoria_id: UUID, mes: int, ano: int) -> Decimal:
        data_inicio = date(ano, mes, 1)
        if mes == 12:
            data_fim = date(ano + 1, 1, 1)
        else:
            data_fim = date(ano, mes + 1, 1)

        subcategories = await self.cat_repo.get_by_user(user_id, tipo=None, ativo_only=None, limit=1000, offset=0)
        sub_ids = [categoria_id] + [c.id for c in subcategories if c.categoria_pai_id == categoria_id]

        valor_gasto = Decimal("0")
        for sub_id in sub_ids:
            gasto = await self.tx_repo.get_category_spending(user_id, sub_id, data_inicio, data_fim)
            valor_gasto += gasto
        return valor_gasto

    async def _to_budget_response(self, budget: Budget) -> BudgetResponse:
        spent = await self._calculate_spent(budget.user_id, budget.categoria_id, budget.mes, budget.ano)
        percentual = float(spent / budget.valor_limite * 100) if budget.valor_limite > 0 else 0.0
        alerta = percentual >= budget.alerta_percentual
        cat = await self.cat_repo.get_by_id(budget.categoria_id, budget.user_id)
        cat_name = cat.nome if cat else ""

        return BudgetResponse(
            id=budget.id,
            user_id=budget.user_id,
            categoria_id=budget.categoria_id,
            categoria_nome=cat_name,
            valor_limite=budget.valor_limite,
            valor_gasto=spent,
            percentual=round(percentual, 2),
            alerta=alerta,
            mes=budget.mes,
            ano=budget.ano,
            alerta_percentual=budget.alerta_percentual,
            criado_em=budget.criado_em,
            atualizado_em=budget.atualizado_em,
        )

    async def create(self, user_id: UUID, data: BudgetCreate) -> BudgetResponse:
        await self._validate_category(user_id, data.categoria_id)

        existing = await self.repo.get_by_categoria_periodo(user_id, data.categoria_id, data.mes, data.ano)
        if existing:
            raise ConflictError("Já existe orçamento para esta categoria no período", "BUDGET_EXISTS")

        budget = Budget(
            user_id=user_id,
            categoria_id=data.categoria_id,
            valor_limite=data.valor_limite,
            mes=data.mes,
            ano=data.ano,
            alerta_percentual=data.alerta_percentual,
        )
        self.db.add(budget)
        await self.db.flush()
        await self.db.refresh(budget)
        return await self._to_budget_response(budget)

    async def get(self, user_id: UUID, budget_id: UUID) -> BudgetResponse:
        budget = await self.repo.get_by_id(budget_id, user_id)
        if not budget:
            raise NotFoundError("Orçamento não encontrado", "BUDGET_NOT_FOUND")
        return await self._to_budget_response(budget)

    async def list(self, user_id: UUID, mes: int | None = None, ano: int | None = None, page: int = 1, size: int = 20):
        budgets = await self.repo.get_by_user(user_id, mes, ano, size, (page - 1) * size)
        total = await self.repo.count_by_user(user_id, mes, ano)
        enriched = [await self._to_budget_response(b) for b in budgets]
        return enriched, total

    async def update(self, user_id: UUID, budget_id: UUID, data: BudgetUpdate) -> BudgetResponse:
        budget = await self.repo.get_by_id(budget_id, user_id)
        if not budget:
            raise NotFoundError("Orçamento não encontrado", "BUDGET_NOT_FOUND")
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(budget, field, value)
        await self.db.flush()
        await self.db.refresh(budget)
        return await self._to_budget_response(budget)

    async def delete(self, user_id: UUID, budget_id: UUID) -> None:
        budget = await self.repo.get_by_id(budget_id, user_id)
        if not budget:
            raise NotFoundError("Orçamento não encontrado", "BUDGET_NOT_FOUND")
        await self.repo.delete(budget)

    async def get_progress(self, user_id: UUID, budget_id: UUID) -> BudgetProgress:
        budget = await self.repo.get_by_id(budget_id, user_id)
        if not budget:
            raise NotFoundError("Orçamento não encontrado", "BUDGET_NOT_FOUND")

        spent = await self._calculate_spent(budget.user_id, budget.categoria_id, budget.mes, budget.ano)
        percentual = float(spent / budget.valor_limite * 100) if budget.valor_limite > 0 else 0.0
        alerta = percentual >= budget.alerta_percentual
        cat = await self.cat_repo.get_by_id(budget.categoria_id, budget.user_id)
        cat_name = cat.nome if cat else ""

        return BudgetProgress(
            budget_id=budget.id,
            categoria_id=budget.categoria_id,
            categoria_nome=cat_name,
            valor_limite=budget.valor_limite,
            valor_gasto=spent,
            percentual=round(percentual, 2),
            alerta=alerta,
            mes=budget.mes,
            ano=budget.ano,
        )
