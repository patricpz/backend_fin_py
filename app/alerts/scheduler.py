import logging
from datetime import datetime, timezone, date
from decimal import Decimal
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select, func, and_
from app.core.config import settings
from app.db.session import async_session_maker
from app.models.user import User
from app.models.transaction import Transaction
from app.models.budget import Budget
from app.models.category import Category
from app.models.enums import TransactionType, TransactionStatus
from app.alerts.rules import check_overspending, check_spending_spike, check_installment_due
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def run_daily_checks() -> None:
    """Verifica excesso de orçamento e picos de gastos para todos os usuários."""
    async with async_session_maker() as db:
        users = (await db.execute(select(User).where(User.ativo == True))).scalars().all()
        service = NotificationService(db)
        today = date.today()

        for user in users:
            try:
                # 1. Verifica orçamentos ativos do mês
                stmt_budgets = select(Budget).join(Category).where(
                    Budget.user_id == user.id,
                    Budget.mes == today.month,
                    Budget.ano == today.year,
                )
                budgets = (await db.execute(stmt_budgets)).scalars().all()

                for b in budgets:
                    # Calcula gastos confirmados na categoria neste mês
                    data_inicio = date(today.year, today.month, 1)
                    stmt_spent = select(func.coalesce(func.sum(Transaction.valor), 0)).where(
                        Transaction.user_id == user.id,
                        Transaction.categoria_id == b.categoria_id,
                        Transaction.tipo == TransactionType.DESPESA,
                        Transaction.status == TransactionStatus.CONFIRMADO,
                        Transaction.data >= data_inicio,
                        Transaction.data <= today,
                    )
                    spent = (await db.execute(stmt_spent)).scalar_one()
                    alert_data = check_overspending(
                        spent=Decimal(str(spent)),
                        budget=Decimal(str(b.valor_limite)),
                        category_name=b.category.nome if b.category else "Categoria",
                    )
                    if alert_data:
                        dedupe_key = f"overspending_{b.categoria_id}_{today.month}_{today.year}_{alert_data['level']}"
                        await service.processar_evento(
                            user_id=user.id,
                            event_type="overspending",
                            data=alert_data,
                            dedupe_key=dedupe_key,
                        )

                # 2. Verifica picos de gastos diários (>= 3x a média diária dos últimos 30 dias)
                stmt_today = select(func.coalesce(func.sum(Transaction.valor), 0)).where(
                    Transaction.user_id == user.id,
                    Transaction.tipo == TransactionType.DESPESA,
                    Transaction.status == TransactionStatus.CONFIRMADO,
                    Transaction.data == today,
                )
                today_spent = Decimal(str((await db.execute(stmt_today)).scalar_one()))

                # Média diária dos últimos 30 dias (excluindo hoje)
                from datetime import timedelta
                past_30 = today - timedelta(days=30)
                stmt_past = select(func.coalesce(func.sum(Transaction.valor), 0)).where(
                    Transaction.user_id == user.id,
                    Transaction.tipo == TransactionType.DESPESA,
                    Transaction.status == TransactionStatus.CONFIRMADO,
                    Transaction.data >= past_30,
                    Transaction.data < today,
                )
                past_spent = Decimal(str((await db.execute(stmt_past)).scalar_one()))
                daily_avg = past_spent / Decimal("30")

                spike_data = check_spending_spike(today_spent=today_spent, daily_average=daily_avg)
                if spike_data:
                    dedupe_key = f"spike_{user.id}_{today.isoformat()}"
                    await service.processar_evento(
                        user_id=user.id,
                        event_type="spending_spike",
                        data=spike_data,
                        dedupe_key=dedupe_key,
                    )

                await db.commit()
            except Exception as e:
                logger.error(f"Erro ao rodar daily checks para user {user.id}: {e}")
                await db.rollback()


async def run_hourly_installment_checks() -> None:
    """Verifica parcelas vencendo nos próximos 3 dias."""
    async with async_session_maker() as db:
        users = (await db.execute(select(User).where(User.ativo == True))).scalars().all()
        service = NotificationService(db)
        today = date.today()

        for user in users:
            try:
                stmt_tx = select(Transaction).where(
                    Transaction.user_id == user.id,
                    Transaction.is_installment == True,
                    Transaction.paid_installments < Transaction.installment_count,
                )
                installments = (await db.execute(stmt_tx)).scalars().all()

                from app.services.expense_service import add_months, calculate_expense_metrics

                for tx in installments:
                    metrics = calculate_expense_metrics(
                        total_amount=Decimal(str(tx.valor)),
                        installment_count=tx.installment_count or 1,
                        paid_installments=tx.paid_installments,
                        first_due_date=tx.first_due_date or tx.data,
                    )
                    next_due = metrics["next_due_date"]
                    if next_due:
                        due_data = check_installment_due(
                            due_date=next_due,
                            today=today,
                            description=tx.descricao,
                            amount=metrics["installment_amount"],
                        )
                        if due_data:
                            dedupe_key = f"installment_due_{tx.id}_{tx.paid_installments + 1}_{next_due.isoformat()}"
                            await service.processar_evento(
                                user_id=user.id,
                                event_type="installment_due",
                                data=due_data,
                                dedupe_key=dedupe_key,
                            )
                await db.commit()
            except Exception as e:
                logger.error(f"Erro ao rodar installment checks para user {user.id}: {e}")
                await db.rollback()


def start_scheduler() -> None:
    if not settings.NOTIFICATION_JOBS_ENABLED:
        return
    scheduler.add_job(
        run_daily_checks,
        "cron",
        hour=8,
        minute=0,
        max_instances=1,
        coalesce=True,
        id="job_diario_alertas",
        replace_existing=True,
    )
    scheduler.add_job(
        run_hourly_installment_checks,
        "interval",
        hours=1,
        max_instances=1,
        coalesce=True,
        id="job_horario_parcelas",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler de notificações iniciado com sucesso.")


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown()
