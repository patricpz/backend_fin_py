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

        stmt = select(
            func.coalesce(func.sum(case((Transaction.tipo == TransactionType.RECEITA, Transaction.valor), else_=0)), 0).label("receitas"),
            func.coalesce(func.sum(case((Transaction.tipo == TransactionType.DESPESA, Transaction.valor), else_=0)), 0).label("despesas"),
            func.coalesce(func.sum(case((Transaction.tipo == TransactionType.TRANSFERENCIA, Transaction.valor), else_=0)), 0).label("transferencias"),
        ).where(
            Transaction.user_id == user_id,
            Transaction.status == TransactionStatus.CONFIRMADO,
            Transaction.data >= data_inicio,
            Transaction.data < data_fim,
        )
        result = await self.db.execute(stmt)
        row = result.one()

        receitas = Decimal(str(row.receitas))
        despesas = Decimal(str(row.despesas))
        transferencias = Decimal(str(row.transferencias))

        return MonthlySummary(
            mes=mes,
            ano=ano,
            total_receitas=receitas,
            total_despesas=despesas,
            saldo=receitas - despesas,
            total_transferencias_enviadas=transferencias,
            total_transferencias_recebidas=Decimal("0"),
        )

    async def category_spending(self, user_id: UUID, mes: int, ano: int) -> CategorySpendingReport:
        data_inicio = date(ano, mes, 1)
        if mes == 12:
            data_fim = date(ano + 1, 1, 1)
        else:
            data_fim = date(ano, mes + 1, 1)

        stmt = select(
            Category.id,
            Category.nome,
            Category.cor,
            Category.icone,
            func.coalesce(func.sum(Transaction.valor), 0).label("valor"),
            Transaction.tipo,
        ).select_from(
            Transaction.__table__.join(Category, Transaction.categoria_id == Category.id, isouter=True)
        ).where(
            Transaction.user_id == user_id,
            Transaction.status == TransactionStatus.CONFIRMADO,
            Transaction.tipo == TransactionType.DESPESA,
            Transaction.data >= data_inicio,
            Transaction.data < data_fim,
        ).group_by(Category.id, Category.nome, Category.cor, Category.icone, Transaction.tipo)

        result = await self.db.execute(stmt)
        rows = result.all()

        total = sum(Decimal(str(r.valor)) for r in rows)
        categorias = [
            CategorySpending(
                categoria_id=r.id or UUID(int=0),
                categoria_nome=r.nome or "Sem categoria",
                cor=r.cor or "#6366F1",
                icone=r.icone or "tag",
                valor=Decimal(str(r.valor)),
                percentual=float(Decimal(str(r.valor)) / total * 100) if total > 0 else 0,
                tipo=r.tipo,
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

        stmt = select(
            Transaction.data,
            func.sum(
                case(
                    (and_(Transaction.tipo == TransactionType.RECEITA, Transaction.status == TransactionStatus.CONFIRMADO), Transaction.valor),
                    (and_(Transaction.tipo == TransactionType.DESPESA, Transaction.status == TransactionStatus.CONFIRMADO), -Transaction.valor),
                    (and_(Transaction.tipo == TransactionType.TRANSFERENCIA, Transaction.status == TransactionStatus.CONFIRMADO, Transaction.conta_id == conta_id), -Transaction.valor),
                    (and_(Transaction.tipo == TransactionType.TRANSFERENCIA, Transaction.status == TransactionStatus.CONFIRMADO, Transaction.conta_destino_id == conta_id), Transaction.valor),
                    else_=0,
                )
            ).label("delta"),
        ).where(
            Transaction.user_id == user_id,
            Transaction.conta_id == conta_id,
            Transaction.data >= data_inicio,
            Transaction.data < data_fim,
        ).group_by(Transaction.data).order_by(Transaction.data)

        result = await self.db.execute(stmt)
        rows = result.all()

        saldo = float(account.saldo_inicial)
        pontos = []
        for r in rows:
            saldo += float(r.delta or 0)
            pontos.append(BalanceEvolutionPoint(data=r.data, saldo=Decimal(str(saldo))))

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