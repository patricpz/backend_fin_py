from decimal import Decimal
from datetime import date as dt_date
from typing import Optional, Dict, Any


def check_overspending(spent: Decimal, budget: Decimal, category_name: str = "") -> Optional[Dict[str, Any]]:
    """
    Verifica excesso de orçamento em categoria nas marcas de 80% e 100%.
    Bordas:
    - 80% exato: dispara alerta de 80%
    - 100% exato: dispara alerta de 100%
    - budget <= 0: retorna None
    """
    if budget <= Decimal("0"):
        return None

    ratio = spent / budget
    percent = round(ratio * Decimal("100"), 2)

    if spent >= budget:
        return {
            "type": "overspending",
            "level": 100,
            "category": category_name,
            "orcado": float(budget),
            "gasto": float(spent),
            "percentual": float(percent),
        }
    elif spent >= (budget * Decimal("0.80")):
        return {
            "type": "overspending",
            "level": 80,
            "category": category_name,
            "orcado": float(budget),
            "gasto": float(spent),
            "percentual": float(percent),
        }

    return None


def check_spending_spike(today_spent: Decimal, daily_average: Decimal) -> Optional[Dict[str, Any]]:
    """
    Verifica pico de gasto diário igual ou superior a 3x a média diária.
    Bordas:
    - daily_average <= 0: retorna None (evita divisão por zero ou falsos positivos com média zero)
    - today_spent >= 3 * daily_average: dispara pico de gasto
    """
    if daily_average <= Decimal("0"):
        return None

    if today_spent <= Decimal("0"):
        return None

    threshold = Decimal("3.0") * daily_average
    if today_spent >= threshold:
        ratio = round(today_spent / daily_average, 2)
        return {
            "type": "spending_spike",
            "today_spent": float(today_spent),
            "daily_average": float(daily_average),
            "ratio": float(ratio),
        }

    return None


def check_installment_due(due_date: dt_date, today: dt_date, description: str = "", amount: Decimal = Decimal("0")) -> Optional[Dict[str, Any]]:
    """
    Verifica parcela de despesa vencendo em até 3 dias (0 <= days_diff <= 3).
    """
    days_diff = (due_date - today).days
    if 0 <= days_diff <= 3:
        return {
            "type": "installment_due",
            "days_left": days_diff,
            "due_date": due_date.isoformat(),
            "description": description,
            "amount": float(amount),
        }

    return None
