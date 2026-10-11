from uuid import UUID
from datetime import date
from decimal import Decimal
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, case
from app.models.transaction import Transaction
from app.models.account import Account
from app.models.category import Category
from app.models.budget import Budget
from app.repositories.transaction_repository import TransactionRepository
from app.repositories.account_repository import AccountRepository
from app.repositories.category_repository import CategoryRepository
from app.repositories.budget_repository import BudgetRepository
from app.schemas.report import (
    MonthlySummary,
    CategorySpendingReport,
    CategorySpending,
    BalanceEvolutionReport,
    BalanceEvolutionPoint,
    BudgetVsActualReport,
    BudgetVsActual,
)
from app.models.enums import TransactionType, TransactionStatus


class ReportService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.tx_repo = TransactionRepository(db)
        self.account_repo = AccountRepository(db)
        self.cat_repo = CategoryRepository(db)
        self.budget_repo = BudgetRepository(db)

    async def monthly_summary(self, user_id: UUID, mes: int, ano: int) -> MonthlySummary:
        data_inicio = date(ano, mes, 1)
        if mes == 12:
            data_fim = date(ano + 1, 1, 1)
        else:
            data_fim = date(ano, mes + 1, 1)

        receitas, despesas, transferencias_enviadas = await self.tx_repo.get_installment_aware_monthly_totals(
            user_id, data_inicio, data_fim
        )

        return MonthlySummary(
            mes=mes,
            ano=ano,
            total_receitas=receitas,
            total_despesas=despesas,
            saldo=receitas - despesas,
            total_transferencias_enviadas=transferencias_enviadas,
            total_transferencias_recebidas=Decimal("0"),
        )

    async def category_spending(self, user_id: UUID, mes: int, ano: int) -> CategorySpendingReport:
        data_inicio = date(ano, mes, 1)
        if mes == 12:
            data_fim = date(ano + 1, 1, 1)
        else:
            data_fim = date(ano, mes + 1, 1)

        rows = await self.tx_repo.get_installment_aware_category_spending(user_id, data_inicio, data_fim)

        total = sum(r[4] for r in rows)
        categorias = [
            CategorySpending(
                categoria_id=r[0],
                categoria_nome=r[1],
                cor=r[2],
                icone=r[3],
                valor=r[4],
                percentual=float(r[4] / total * 100) if total > 0 else 0,
                tipo=r[5],
            )
            for r in rows
        ]

        return CategorySpendingReport(mes=mes, ano=ano, total_despesas=total, categorias=categorias)

    async def balance_evolution(self, user_id: UUID, conta_id: UUID, mes: int, ano: int) -> BalanceEvolutionReport:
        data_inicio = date(ano, mes, 1)
        if mes == 12:
            data_fim = date(ano + 1, 1, 1)
        else:
            data_fim = date(ano, mes + 1, 1)

        account = await self.account_repo.get_by_id(conta_id, user_id)
        if not account:
            from app.core.exceptions import NotFoundError
            raise NotFoundError("Conta não encontrada", "ACCOUNT_NOT_FOUND")

        deltas = await self.tx_repo.get_installment_aware_balance_delta_for_account(
            user_id, conta_id, data_inicio, data_fim
        )

        saldo = Decimal(str(account.saldo_inicial))
        pontos = []
        for data, delta in deltas:
            saldo += delta
            pontos.append(BalanceEvolutionPoint(data=data, saldo=saldo))

        return BalanceEvolutionReport(conta_id=account.id, conta_nome=account.nome, pontos=pontos)

    async def budget_vs_actual(self, user_id: UUID, mes: int, ano: int) -> BudgetVsActualReport:
        budgets = await self.budget_repo.get_by_user(user_id, mes, ano, 1000, 0)

        orcamentos = []
        for b in budgets:
            data_inicio = date(ano, mes, 1)
            if mes == 12:
                data_fim = date(ano + 1, 1, 1)
            else:
                data_fim = date(ano, mes + 1, 1)

            from app.repositories.category_repository import CategoryRepository
            cat_repo = CategoryRepository(self.db)
            subcategories = await cat_repo.get_by_user(user_id, tipo=None, ativo_only=True, limit=1000, offset=0)
            sub_ids = [b.categoria_id] + [c.id for c in subcategories if c.categoria_pai_id == b.categoria_id]

            valor_gasto = Decimal("0")
            for sub_id in sub_ids:
                gasto = await self.tx_repo.get_category_spending(user_id, sub_id, data_inicio, data_fim)
                valor_gasto += gasto

            percentual = float(valor_gasto / b.valor_limite * 100) if b.valor_limite > 0 else 0
            alerta = percentual >= b.alerta_percentual

            orcamentos.append(BudgetVsActual(
                categoria_id=b.categoria_id,
                categoria_nome=b.category.nome,
                orcado=b.valor_limite,
                realizado=valor_gasto,
                percentual=percentual,
                alerta=alerta,
            ))

        return BudgetVsActualReport(mes=mes, ano=ano, orcamentos=orcamentos)