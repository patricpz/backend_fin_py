from typing import Optional, Sequence, List
from uuid import UUID
from datetime import date
from decimal import Decimal
from collections import defaultdict
from sqlalchemy import select, func, and_, or_, case
from sqlalchemy.orm import selectinload, outerjoin
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base import BaseRepository
from app.models.transaction import Transaction
from app.models.installment import Installment
from app.models.category import Category
from app.models.enums import TransactionType, TransactionStatus
from app.schemas.transaction import TransactionFilters


class TransactionRepository(BaseRepository[Transaction]):
    def __init__(self, db: AsyncSession):
        super().__init__(Transaction, db)

    async def get_by_user(
        self,
        user_id: UUID,
        filters: Optional[TransactionFilters] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Sequence[Transaction]:
        stmt = select(Transaction).where(Transaction.user_id == user_id)

        if filters:
            if filters.conta_id:
                stmt = stmt.where(
                    or_(
                        Transaction.conta_id == filters.conta_id,
                        and_(
                            Transaction.tipo == TransactionType.TRANSFERENCIA,
                            Transaction.conta_destino_id == filters.conta_id,
                        ),
                    )
                )
            if filters.categoria_id:
                stmt = stmt.where(Transaction.categoria_id == filters.categoria_id)
            if filters.tipo:
                stmt = stmt.where(Transaction.tipo == filters.tipo)
            if filters.status:
                stmt = stmt.where(Transaction.status == filters.status)
            if filters.data_inicio:
                stmt = stmt.where(Transaction.data >= filters.data_inicio)
            if filters.data_fim:
                stmt = stmt.where(Transaction.data <= filters.data_fim)
            if filters.descricao:
                stmt = stmt.where(Transaction.descricao.ilike(f"%{filters.descricao}%"))
            if filters.is_installment is not None:
                stmt = stmt.where(Transaction.is_installment == filters.is_installment)
            if filters.completed is not None:
                if filters.completed:
                    stmt = stmt.where(Transaction.paid_installments >= Transaction.installment_count)
                else:
                    stmt = stmt.where(Transaction.paid_installments < Transaction.installment_count)

        stmt = stmt.order_by(Transaction.data.desc(), Transaction.criado_em.desc()).limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_all_by_user(
        self,
        user_id: UUID,
        filters: Optional[TransactionFilters] = None,
    ) -> Sequence[Transaction]:
        stmt = select(Transaction).where(Transaction.user_id == user_id)

        if filters:
            if filters.conta_id:
                stmt = stmt.where(
                    or_(
                        Transaction.conta_id == filters.conta_id,
                        and_(
                            Transaction.tipo == TransactionType.TRANSFERENCIA,
                            Transaction.conta_destino_id == filters.conta_id,
                        ),
                    )
                )
            if filters.categoria_id:
                stmt = stmt.where(Transaction.categoria_id == filters.categoria_id)
            if filters.tipo:
                stmt = stmt.where(Transaction.tipo == filters.tipo)
            if filters.status:
                stmt = stmt.where(Transaction.status == filters.status)
            if filters.data_inicio:
                stmt = stmt.where(Transaction.data >= filters.data_inicio)
            if filters.data_fim:
                stmt = stmt.where(Transaction.data <= filters.data_fim)
            if filters.descricao:
                stmt = stmt.where(Transaction.descricao.ilike(f"%{filters.descricao}%"))
            if filters.is_installment is not None:
                stmt = stmt.where(Transaction.is_installment == filters.is_installment)
            if filters.completed is not None:
                if filters.completed:
                    stmt = stmt.where(Transaction.paid_installments >= Transaction.installment_count)
                else:
                    stmt = stmt.where(Transaction.paid_installments < Transaction.installment_count)

        stmt = stmt.order_by(Transaction.data.desc(), Transaction.criado_em.desc())
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def count_by_user(self, user_id: UUID, filters: Optional[TransactionFilters] = None) -> int:
        stmt = select(func.count()).select_from(Transaction).where(Transaction.user_id == user_id)

        if filters:
            if filters.conta_id:
                stmt = stmt.where(
                    or_(
                        Transaction.conta_id == filters.conta_id,
                        and_(
                            Transaction.tipo == TransactionType.TRANSFERENCIA,
                            Transaction.conta_destino_id == filters.conta_id,
                        ),
                    )
                )
            if filters.categoria_id:
                stmt = stmt.where(Transaction.categoria_id == filters.categoria_id)
            if filters.tipo:
                stmt = stmt.where(Transaction.tipo == filters.tipo)
            if filters.status:
                stmt = stmt.where(Transaction.status == filters.status)
            if filters.data_inicio:
                stmt = stmt.where(Transaction.data >= filters.data_inicio)
            if filters.data_fim:
                stmt = stmt.where(Transaction.data <= filters.data_fim)
            if filters.descricao:
                stmt = stmt.where(Transaction.descricao.ilike(f"%{filters.descricao}%"))
            if filters.is_installment is not None:
                stmt = stmt.where(Transaction.is_installment == filters.is_installment)
            if filters.completed is not None:
                if filters.completed:
                    stmt = stmt.where(Transaction.paid_installments >= Transaction.installment_count)
                else:
                    stmt = stmt.where(Transaction.paid_installments < Transaction.installment_count)

        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def get_by_id(self, id: UUID, user_id: UUID) -> Optional[Transaction]:
        result = await self.db.execute(select(Transaction).where(Transaction.id == id, Transaction.user_id == user_id))
        return result.scalar_one_or_none()

    async def get_by_id_with_installments(self, id: UUID, user_id: UUID) -> Optional[Transaction]:
        stmt = (
            select(Transaction)
            .where(Transaction.id == id, Transaction.user_id == user_id)
            .options(selectinload(Transaction.installments))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_idempotency_key(self, user_id: UUID, key: UUID) -> Optional[Transaction]:
        result = await self.db.execute(
            select(Transaction).where(Transaction.user_id == user_id, Transaction.idempotency_key == key)
        )
        return result.scalar_one_or_none()

    async def get_installment_aware_monthly_totals(
        self,
        user_id: UUID,
        data_inicio: date,
        data_fim: date,
    ) -> tuple[Decimal, Decimal, Decimal]:
        """
        Returns (receitas, despesas, transferencias_enviadas) considering:
        - installment recognition by Installment.data_vencimento (confirmed installments only)
        - non-installment recognition by Transaction.data for transactions without installments
        """
        # Installment-based recognition: simple filtered aggregates per type.
        # Evitar CAST(installments.valor AS NUMERIC) porque no SQLite retorna
        # valores com escala estranha (ex: 0E-10) mesmo quando o resultado correto existe.
        async def _sum(filtered_stmt):
            row = await self.db.execute(filtered_stmt)
            raw = row.scalar_one() or 0
            if isinstance(raw, Decimal):
                return raw
            return Decimal(str(raw))

        receitas_inst = await _sum(
            select(func.coalesce(func.sum(Installment.valor), 0))
            .join(Transaction, Installment.transaction_id == Transaction.id)
            .where(
                Installment.data_vencimento >= data_inicio,
                Installment.data_vencimento < data_fim,
                Transaction.user_id == user_id,
                Installment.status == TransactionStatus.CONFIRMADO,
                Transaction.tipo == TransactionType.RECEITA,
            )
        )
        despesas_inst = await _sum(
            select(func.coalesce(func.sum(Installment.valor), 0))
            .join(Transaction, Installment.transaction_id == Transaction.id)
            .where(
                Installment.data_vencimento >= data_inicio,
                Installment.data_vencimento < data_fim,
                Transaction.user_id == user_id,
                Installment.status == TransactionStatus.CONFIRMADO,
                Transaction.tipo == TransactionType.DESPESA,
            )
        )
        transferencias_inst = await _sum(
            select(func.coalesce(func.sum(Installment.valor), 0))
            .join(Transaction, Installment.transaction_id == Transaction.id)
            .where(
                Installment.data_vencimento >= data_inicio,
                Installment.data_vencimento < data_fim,
                Transaction.user_id == user_id,
                Installment.status == TransactionStatus.CONFIRMADO,
                Transaction.tipo == TransactionType.TRANSFERENCIA,
            )
        )

        # Non-installment transactions: transactions that exist in the period and have no installments at all
        stmt_tx = (
            select(
                func.coalesce(func.sum(case((and_(Transaction.tipo == TransactionType.RECEITA, Transaction.status == TransactionStatus.CONFIRMADO, ~Transaction.installments.any()), Transaction.valor), else_=0)), 0).label("receitas_tx"),
                func.coalesce(func.sum(case((and_(Transaction.tipo == TransactionType.DESPESA, Transaction.status == TransactionStatus.CONFIRMADO, ~Transaction.installments.any()), Transaction.valor), else_=0)), 0).label("despesas_tx"),
                func.coalesce(func.sum(case((and_(Transaction.tipo == TransactionType.TRANSFERENCIA, Transaction.status == TransactionStatus.CONFIRMADO, ~Transaction.installments.any()), Transaction.valor), else_=0)), 0).label("transferencias_tx"),
            )
            .where(
                Transaction.user_id == user_id,
                Transaction.data >= data_inicio,
                Transaction.data < data_fim,
            )
        )

        tx_row = await self.db.execute(stmt_tx)
        tx_data = tx_row.one()

        receitas = Decimal(str(tx_data.receitas_tx or 0)) + receitas_inst
        despesas = Decimal(str(tx_data.despesas_tx or 0)) + despesas_inst
        transferencias_enviadas = Decimal(str(tx_data.transferencias_tx or 0)) + transferencias_inst

        return receitas, despesas, transferencias_enviadas

    async def get_installment_aware_category_spending(
        self,
        user_id: UUID,
        data_inicio: date,
        data_fim: date,
    ) -> List[tuple[UUID, str, str, str, Decimal, str]]:
        """
        Returns rows: (category_id, category_name, cor, icone, valor, tipo)
        Considers:
        - non-installment expenses by Transaction.data
        - confirmed expense installments by Installment.data_vencimento
        """
        stmt_tx = (
            select(
                Category.id,
                Category.nome,
                Category.cor,
                Category.icone,
                func.coalesce(func.sum(Transaction.valor), 0).label("valor"),
                Transaction.tipo,
            )
            .select_from(
                Transaction.__table__.outerjoin(Category, Transaction.categoria_id == Category.id)
            )
            .where(
                Transaction.user_id == user_id,
                Transaction.status == TransactionStatus.CONFIRMADO,
                Transaction.tipo == TransactionType.DESPESA,
                Transaction.data >= data_inicio,
                Transaction.data < data_fim,
                ~Transaction.installments.any(),
            )
            .group_by(Category.id, Category.nome, Category.cor, Category.icone, Transaction.tipo)
        )

        stmt_inst = (
            select(
                Category.id,
                Category.nome,
                Category.cor,
                Category.icone,
                func.coalesce(func.sum(Installment.valor), 0).label("valor"),
                Transaction.tipo,
            )
            .select_from(Installment)
            .join(Transaction, Installment.transaction_id == Transaction.id)
            .outerjoin(Category, Transaction.categoria_id == Category.id)
            .where(
                Installment.data_vencimento >= data_inicio,
                Installment.data_vencimento < data_fim,
                Installment.status == TransactionStatus.CONFIRMADO,
                Transaction.user_id == user_id,
                Transaction.tipo == TransactionType.DESPESA,
            )
            .group_by(Category.id, Category.nome, Category.cor, Category.icone, Transaction.tipo)
        )

        tx_rows = (await self.db.execute(stmt_tx)).all()
        inst_rows = (await self.db.execute(stmt_inst)).all()

        combined = defaultdict(lambda: [UUID(int=0), "", "#6366F1", "tag", Decimal("0"), "despesa"])
        for r in tx_rows:
            combined[r.id][0] = r.id
            combined[r.id][1] = r.nome or "Sem categoria"
            combined[r.id][2] = r.cor or "#6366F1"
            combined[r.id][3] = r.icone or "tag"
            combined[r.id][4] += Decimal(str(r.valor))
            combined[r.id][5] = r.tipo

        for r in inst_rows:
            key = r.id
            combined[key][0] = r.id
            combined[key][1] = r.nome or "Sem categoria"
            combined[key][2] = r.cor or "#6366F1"
            combined[key][3] = r.icone or "tag"
            combined[key][4] += Decimal(str(r.valor))
            combined[key][5] = r.tipo

        result = []
        for key, v in combined.items():
            if v[4] > 0:
                result.append(tuple(v))

        return result

    async def get_installment_aware_balance_delta_for_account(
        self,
        user_id: UUID,
        conta_id: UUID,
        data_inicio: date,
        data_fim: date,
    ) -> List[tuple[date, Decimal]]:
        """
        Returns list of (data, delta) points for balance evolution.
        Uses:
        - non-installment transactions by Transaction.data
        - installment movements by Installment.data_vencimento
        """
        stmt_tx = (
            select(
                Transaction.data,
                func.sum(
                    case(
                        (and_(Transaction.tipo == TransactionType.RECEITA, Transaction.status == TransactionStatus.CONFIRMADO, ~Transaction.installments.any()), Transaction.valor),
                        (and_(Transaction.tipo == TransactionType.DESPESA, Transaction.status == TransactionStatus.CONFIRMADO, ~Transaction.installments.any()), -Transaction.valor),
                        (and_(Transaction.tipo == TransactionType.TRANSFERENCIA, Transaction.status == TransactionStatus.CONFIRMADO, Transaction.conta_id == conta_id), -Transaction.valor),
                        (and_(Transaction.tipo == TransactionType.TRANSFERENCIA, Transaction.status == TransactionStatus.CONFIRMADO, Transaction.conta_destino_id == conta_id), Transaction.valor),
                        else_=0,
                    )
                ).label("delta"),
            )
            .where(
                Transaction.user_id == user_id,
                or_(
                    Transaction.conta_id == conta_id,
                    and_(
                        Transaction.tipo == TransactionType.TRANSFERENCIA,
                        Transaction.conta_destino_id == conta_id,
                    ),
                ),
                Transaction.data >= data_inicio,
                Transaction.data < data_fim,
            )
            .group_by(Transaction.data)
            .order_by(Transaction.data)
        )

        stmt_inst = (
            select(
                Installment.data_vencimento,
                func.sum(
                    case(
                        (and_(Installment.status == TransactionStatus.CONFIRMADO, Transaction.tipo == TransactionType.RECEITA), Installment.valor),
                        (and_(Installment.status == TransactionStatus.CONFIRMADO, Transaction.tipo == TransactionType.DESPESA), -Installment.valor),
                        else_=0,
                    )
                ).label("delta"),
            )
            .select_from(Installment)
            .join(Transaction, Installment.transaction_id == Transaction.id)
            .where(
                Installment.data_vencimento >= data_inicio,
                Installment.data_vencimento < data_fim,
                Transaction.user_id == user_id,
                Transaction.conta_id == conta_id,
            )
            .group_by(Installment.data_vencimento)
            .order_by(Installment.data_vencimento)
        )

        tx_rows = (await self.db.execute(stmt_tx)).all()
        inst_rows = (await self.db.execute(stmt_inst)).all()

        points = defaultdict(Decimal)
        for r in tx_rows:
            points[r.data] += Decimal(str(r.delta or 0))
        for r in inst_rows:
            points[r.data_vencimento] += Decimal(str(r.delta or 0))

        result = []
        for data, delta in sorted(points.items()):
            if delta != 0:
                result.append((data, delta))

        return result

    async def has_transactions(self, account_id: UUID) -> bool:
        from sqlalchemy import exists, or_
        result = await self.db.execute(
            select(exists()).where(
                or_(
                    Transaction.conta_id == account_id,
                    Transaction.conta_destino_id == account_id,
                )
            )
        )
        return bool(result.scalar_one())

    async def get_account_balance(self, account_id: UUID) -> Decimal:
        stmt_rec = select(func.coalesce(func.sum(Transaction.valor), 0)).where(
            Transaction.conta_id == account_id,
            Transaction.status == TransactionStatus.CONFIRMADO,
            Transaction.tipo == TransactionType.RECEITA,
        )
        receitas = (await self.db.execute(stmt_rec)).scalar_one()

        stmt_desp = select(func.coalesce(func.sum(Transaction.valor), 0)).where(
            Transaction.conta_id == account_id,
            Transaction.status == TransactionStatus.CONFIRMADO,
            Transaction.tipo == TransactionType.DESPESA,
        )
        despesas = (await self.db.execute(stmt_desp)).scalar_one()

        stmt_transf_env = select(func.coalesce(func.sum(Transaction.valor), 0)).where(
            Transaction.conta_id == account_id,
            Transaction.status == TransactionStatus.CONFIRMADO,
            Transaction.tipo == TransactionType.TRANSFERENCIA,
        )
        transferencias_enviadas = (await self.db.execute(stmt_transf_env)).scalar_one()

        stmt_transf_rec = select(func.coalesce(func.sum(Transaction.valor), 0)).where(
            Transaction.conta_destino_id == account_id,
            Transaction.status == TransactionStatus.CONFIRMADO,
            Transaction.tipo == TransactionType.TRANSFERENCIA,
        )
        transferencias_recebidas = (await self.db.execute(stmt_transf_rec)).scalar_one()

        return (
            Decimal(str(receitas))
            - Decimal(str(despesas))
            - Decimal(str(transferencias_enviadas))
            + Decimal(str(transferencias_recebidas))
        )

    async def get_category_spending(self, user_id: UUID, categoria_id: UUID, data_inicio: date, data_fim: date) -> Decimal:
        from app.models.category import Category
        stmt = select(func.coalesce(func.sum(Transaction.valor), 0)).where(
            Transaction.user_id == user_id,
            Transaction.status == TransactionStatus.CONFIRMADO,
            Transaction.tipo == TransactionType.DESPESA,
            Transaction.data >= data_inicio,
            Transaction.data <= data_fim,
            Transaction.categoria_id == categoria_id
        )
        result = await self.db.execute(stmt)
        return Decimal(str(result.scalar_one()))

    async def get_account_monthly_totals(
        self,
        user_id: UUID,
        conta_id: UUID,
        data_inicio: date,
        data_fim: date,
    ) -> tuple[Decimal, Decimal]:
        stmt = (
            select(
                func.coalesce(func.sum(case((and_(Transaction.tipo == TransactionType.RECEITA, Transaction.status == TransactionStatus.CONFIRMADO), Transaction.valor), else_=0)), 0).label("receitas"),
                func.coalesce(func.sum(case((and_(Transaction.tipo == TransactionType.DESPESA, Transaction.status == TransactionStatus.CONFIRMADO), Transaction.valor), else_=0)), 0).label("despesas"),
            )
            .where(
                Transaction.user_id == user_id,
                or_(
                    Transaction.conta_id == conta_id,
                    and_(
                        Transaction.tipo == TransactionType.TRANSFERENCIA,
                        Transaction.conta_destino_id == conta_id,
                    ),
                ),
                Transaction.data >= data_inicio,
                Transaction.data < data_fim,
            )
        )
        row = (await self.db.execute(stmt)).one()
        return Decimal(str(row.receitas or 0)), Decimal(str(row.despesas or 0))

    async def get_monthly_totals_for_year(
        self,
        user_id: UUID,
        ano: int,
        conta_id: Optional[UUID] = None,
    ) -> list[tuple[int, Decimal, Decimal, Decimal]]:
        results = []
        for mes in range(1, 13):
            data_inicio = date(ano, mes, 1)
            if mes == 12:
                data_fim = date(ano + 1, 1, 1)
            else:
                data_fim = date(ano, mes + 1, 1)

            if conta_id:
                receitas, despesas = await self.get_account_monthly_totals(user_id, conta_id, data_inicio, data_fim)
            else:
                receitas, despesas, _ = await self.get_installment_aware_monthly_totals(user_id, data_inicio, data_fim)

            results.append((mes, receitas, despesas, receitas - despesas))
        return results
