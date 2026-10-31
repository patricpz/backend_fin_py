from typing import Dict, Any, Tuple
from abc import ABC, abstractmethod
from app.core.config import settings


class InsightProvider(ABC):
    @abstractmethod
    def generate_text(self, event_type: str, data: Dict[str, Any]) -> Tuple[str, str, Dict[str, Any]]:
        """Retorna (title, body, payload)"""
        pass


class TemplateProvider(InsightProvider):
    def generate_text(self, event_type: str, data: Dict[str, Any]) -> Tuple[str, str, Dict[str, Any]]:
        payload = dict(data)
        if event_type == "overspending":
            category = data.get("category", "Categoria")
            gasto = data.get("gasto", 0)
            orcado = data.get("orcado", 0)
            level = data.get("level", 100)
            percentual = data.get("percentual", 100)

            if level >= 100:
                title = f"{category} passou do limite"
                body = f"Você gastou R$ {gasto:,.2f} de R$ {orcado:,.2f} este mês.".replace(",", "X").replace(".", ",").replace("X", ".")
            else:
                title = f"Atenção aos gastos com {category}"
                body = f"Você atingiu {int(percentual)}% do orçamento de R$ {orcado:,.2f}.".replace(",", "X").replace(".", ",").replace("X", ".")

            payload.setdefault("categoria", category)
            payload.setdefault("orcado", orcado)
            payload.setdefault("gasto", gasto)
            payload.setdefault("percentual", percentual)
            return title, body, payload

        elif event_type == "spending_spike":
            today_spent = data.get("today_spent", 0)
            ratio = data.get("ratio", 3)
            title = "Pico de gastos detectado"
            body = f"Você gastou R$ {today_spent:,.2f} hoje, cerca de {ratio}x a sua média diária.".replace(",", "X").replace(".", ",").replace("X", ".")
            return title, body, payload

        elif event_type == "installment_due":
            description = data.get("description", "Despesa")
            days_left = data.get("days_left", 0)
            amount = data.get("amount", 0)

            if days_left == 0:
                title = f"Parcela de {description} vence hoje"
                body = f"A parcela no valor de R$ {amount:,.2f} vence hoje.".replace(",", "X").replace(".", ",").replace("X", ".")
            else:
                title = f"Parcela de {description} vence em {days_left} dias"
                body = f"A parcela no valor de R$ {amount:,.2f} vence em {days_left} dias.".replace(",", "X").replace(".", ",").replace("X", ".")
            return title, body, payload

        elif event_type == "summary":
            title = "Resumo financeiro"
            body = data.get("message", "Veja seu resumo financeiro atualizado no app.")
            return title, body, payload

        elif event_type == "tip":
            title = "Dica financeira"
            body = data.get("message", "Acompanhe seus limites de gastos para manter o orçamento equilibrado.")
            return title, body, payload

        title = data.get("title", "Notificação Financeira")
        body = data.get("body", "Você tem uma nova notificação financeira.")
        return title, body, payload


def get_insight_provider() -> InsightProvider:
    provider_name = settings.NOTIFICATION_PROVIDER.lower()
    if provider_name == "template":
        return TemplateProvider()
    # Se gemini for solicitado futuramente, retorna TemplateProvider como fallback
    return TemplateProvider()
