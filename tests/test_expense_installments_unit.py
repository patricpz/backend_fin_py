from decimal import Decimal
from datetime import date
import pytest
from app.services.expense_service import add_months, calculate_expense_metrics
from app.alerts.rules import check_overspending, check_spending_spike, check_installment_due
from app.services.notification_service import NotificationService


def test_calculate_installments_cents_adjustment_1000_div_3():
    """1000 dividido em 3 parcelas: 333.33 + 333.33 + 333.34 = 1000.00"""
    metrics = calculate_expense_metrics(
        total_amount=Decimal("1000.00"),
        installment_count=3,
        paid_installments=0,
        first_due_date=date(2026, 8, 10),
    )
    assert metrics["installment_amount"] == Decimal("333.33")
    assert metrics["last_installment_amount"] == Decimal("333.34")

    # Verifica soma de todas as parcelas
    base = metrics["installment_amount"]
    last = metrics["last_installment_amount"]
    total_sum = (base * 2) + last
    assert total_sum == Decimal("1000.00")


def test_calculate_installments_cents_adjustment_3000_div_7():
    """3000 dividido em 7 parcelas: 6 de 428.57 + 1 de 428.58 = 3000.00"""
    metrics = calculate_expense_metrics(
        total_amount=Decimal("3000.00"),
        installment_count=7,
        paid_installments=0,
        first_due_date=date(2026, 8, 10),
    )
    assert metrics["installment_amount"] == Decimal("428.57")
    assert metrics["last_installment_amount"] == Decimal("428.58")

    base = metrics["installment_amount"]
    last = metrics["last_installment_amount"]
    total_sum = (base * 6) + last
    assert total_sum == Decimal("3000.00")


def test_progress_percent_borders_and_rounding():
    d = date(2026, 1, 10)
    # Borda 0%
    m0 = calculate_expense_metrics(Decimal("1000.00"), 10, 0, d)
    assert m0["progress_percent"] == 0
    assert m0["is_completed"] is False

    # Borda 50%
    m50 = calculate_expense_metrics(Decimal("1000.00"), 10, 5, d)
    assert m50["progress_percent"] == 50
    assert m50["is_completed"] is False

    # Borda 100%
    m100 = calculate_expense_metrics(Decimal("1000.00"), 10, 10, d)
    assert m100["progress_percent"] == 100
    assert m100["is_completed"] is True
    assert m100["next_due_date"] is None
    assert m100["paid_amount"] == Decimal("1000.00")
    assert m100["remaining_amount"] == Decimal("0.00")

    # Arredondamento ROUND_HALF_UP (1 de 3 = 33.33% -> 33%, 2 de 3 = 66.67% -> 67%)
    m33 = calculate_expense_metrics(Decimal("300.00"), 3, 1, d)
    assert m33["progress_percent"] == 33

    m67 = calculate_expense_metrics(Decimal("300.00"), 3, 2, d)
    assert m67["progress_percent"] == 67


def test_next_due_date_leap_year_and_month_end():
    # 31 de janeiro de 2026 (ano não-bissexto) + 1 mês = 28 de fevereiro de 2026
    d2026 = add_months(date(2026, 1, 31), 1)
    assert d2026 == date(2026, 2, 28)

    # 31 de janeiro de 2028 (ano bissexto) + 1 mês = 29 de fevereiro de 2028
    d2028 = add_months(date(2028, 1, 31), 1)
    assert d2028 == date(2028, 2, 29)

    # 31 de março + 1 mês = 30 de abril
    d_apr = add_months(date(2026, 3, 31), 1)
    assert d_apr == date(2026, 4, 30)

    # 31 de dezembro + 2 meses = 28 de fevereiro do ano seguinte
    d_dec = add_months(date(2026, 12, 31), 2)
    assert d_dec == date(2027, 2, 28)


def test_alert_rules_edge_cases():
    # 80% exato de 1000 = 800
    res_80 = check_overspending(Decimal("800.00"), Decimal("1000.00"), "Transporte")
    assert res_80 is not None
    assert res_80["level"] == 80
    assert res_80["percentual"] == 80.0

    # 79.99% não deve disparar
    res_79 = check_overspending(Decimal("799.99"), Decimal("1000.00"), "Transporte")
    assert res_79 is None

    # 100% exato de 1000 = 1000
    res_100 = check_overspending(Decimal("1000.00"), Decimal("1000.00"), "Transporte")
    assert res_100 is not None
    assert res_100["level"] == 100
    assert res_100["percentual"] == 100.0

    # Orçamento zero não dispara
    assert check_overspending(Decimal("100.00"), Decimal("0.00"), "Zero") is None

    # Spike: média diária zero retorna None
    assert check_spending_spike(Decimal("500.00"), Decimal("0.00")) is None

    # Spike: gasto exatamente 3x a média diária dispara
    res_spike = check_spending_spike(Decimal("300.00"), Decimal("100.00"))
    assert res_spike is not None
    assert res_spike["ratio"] == 3.0

    # Spike: abaixo de 3x não dispara
    assert check_spending_spike(Decimal("299.99"), Decimal("100.00")) is None

    # Parcela: vencendo hoje (0 dias)
    d_today = date(2026, 8, 15)
    due_0 = check_installment_due(d_today, d_today, "Notebook", Decimal("250.00"))
    assert due_0 is not None
    assert due_0["days_left"] == 0

    # Parcela: vencendo em 3 dias
    due_3 = check_installment_due(date(2026, 8, 18), d_today, "Notebook", Decimal("250.00"))
    assert due_3 is not None
    assert due_3["days_left"] == 3

    # Parcela: vencendo em 4 dias (fora da janela)
    due_4 = check_installment_due(date(2026, 8, 19), d_today, "Notebook", Decimal("250.00"))
    assert due_4 is None


def test_quiet_hours_and_timezone_validation():
    from datetime import datetime, timezone
    import zoneinfo

    # Instância do NotificationService com dummy db
    service = NotificationService(db=None)

    # Fuso de Fortaleza
    tz_br = zoneinfo.ZoneInfo("America/Fortaleza")

    # Horário normal: 23:30 (dentro de 22:00 até 07:00)
    dt_quiet_night = datetime(2026, 10, 31, 23, 30, tzinfo=tz_br)
    assert service._is_quiet_hours(dt_quiet_night, "22:00", "07:00") is True

    # Horário normal: 03:00 da manhã (dentro de 22:00 até 07:00)
    dt_quiet_dawn = datetime(2026, 10, 31, 3, 0, tzinfo=tz_br)
    assert service._is_quiet_hours(dt_quiet_dawn, "22:00", "07:00") is True

    # Horário acordado: 14:00 (fora de 22:00 até 07:00)
    dt_active = datetime(2026, 10, 31, 14, 0, tzinfo=tz_br)
    assert service._is_quiet_hours(dt_active, "22:00", "07:00") is False

    # Quiet hours nulo
    assert service._is_quiet_hours(dt_quiet_night, None, None) is False
