from uuid import UUID
from datetime import date
from decimal import Decimal
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
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
    MonthlyBalanceEvolution,
    BudgetVsActualReport,
    BudgetVsActual,
)
from app.core.exceptions import NotFoundError


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
                percentual=round(float(r[4] / total * 100), 2) if total > 0 else 0.0,
                tipo=r[5],
            )
            for r in rows
        ]

        return CategorySpendingReport(mes=mes, ano=ano, total_despesas=total, categorias=categorias)

    async def balance_evolution_daily(self, user_id: UUID, conta_id: UUID, mes: int, ano: int) -> BalanceEvolutionReport:
        data_inicio = date(ano, mes, 1)
        if mes == 12:
            data_fim = date(ano + 1, 1, 1)
        else:
            data_fim = date(ano, mes + 1, 1)

        account = await self.account_repo.get_by_id(conta_id, user_id)
        if not account:
            raise NotFoundError("Conta não encontrada", "ACCOUNT_NOT_FOUND")

        deltas = await self.tx_repo.get_installment_aware_balance_delta_for_account(
            user_id, conta_id, data_inicio, data_fim
        )

        saldo = Decimal(str(account.saldo_inicial))
        pontos = []
        for d, delta in deltas:
            saldo += delta
            pontos.append(BalanceEvolutionPoint(data=d, saldo=saldo))

        return BalanceEvolutionReport(conta_id=account.id, conta_nome=account.nome, pontos=pontos)

    async def balance_evolution_yearly(
        self,
        user_id: UUID,
        ano: int,
        conta_id: Optional[UUID] = None,
    ) -> List[MonthlyBalanceEvolution]:
        if conta_id:
            account = await self.account_repo.get_by_id(conta_id, user_id)
            if not account:
                raise NotFoundError("Conta não encontrada", "ACCOUNT_NOT_FOUND")

        totals = await self.tx_repo.get_monthly_totals_for_year(user_id, ano, conta_id)
        return [
            MonthlyBalanceEvolution(
                mes=m,
                ano=ano,
                total_receitas=r,
                total_despesas=d,
                saldo=s,
            )
            for m, r, d, s in totals
        ]

    async def budget_vs_actual(self, user_id: UUID, mes: int, ano: int) -> BudgetVsActualReport:
        budgets = await self.budget_repo.get_by_user(user_id, mes, ano, 1000, 0)

        orcamentos = []
        for b in budgets:
            data_inicio = date(ano, mes, 1)
            if mes == 12:
                data_fim = date(ano + 1, 1, 1)
            else:
                data_fim = date(ano, mes + 1, 1)

            subcategories = await self.cat_repo.get_by_user(user_id, tipo=None, ativo_only=None, limit=1000, offset=0)
            sub_ids = [b.categoria_id] + [c.id for c in subcategories if c.categoria_pai_id == b.categoria_id]

            valor_gasto = Decimal("0")
            for sub_id in sub_ids:
                gasto = await self.tx_repo.get_category_spending(user_id, sub_id, data_inicio, data_fim)
                valor_gasto += gasto

            percentual = float(valor_gasto / b.valor_limite * 100) if b.valor_limite > 0 else 0.0
            alerta = percentual >= b.alerta_percentual
            cat = await self.cat_repo.get_by_id(b.categoria_id, user_id)
            cat_name = cat.nome if cat else ""

            orcamentos.append(BudgetVsActual(
                categoria_id=b.categoria_id,
                categoria_nome=cat_name,
                orcado=b.valor_limite,
                realizado=valor_gasto,
                diferenca=b.valor_limite - valor_gasto,
                percentual=round(percentual, 2),
                alerta=alerta,
            ))

        return BudgetVsActualReport(mes=mes, ano=ano, orcamentos=orcamentos)
