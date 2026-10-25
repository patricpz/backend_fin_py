import json
from typing import Any

from .client import GoogleGenAIClient
from .prompts import ANALYSIS_PROMPT, DIAGNOSTIC_PROMPT, ECONOMY_REPORT_PROMPT


class FinancialAIAssistant:
    def __init__(self, ai_client: GoogleGenAIClient | None = None):
        self.ai_client = ai_client or GoogleGenAIClient()

    def analyze_expenses(self, user_data: dict[str, Any], period: str = "mês atual") -> dict[str, Any]:
        """Analisa os gastos do usuário e identifica oportunidades de redução.

        Args:
            user_data: Dados financeiros do usuário (incluindo transações, categorias, etc.)
            period: Período para análise

        Returns:
            Análise estruturada dos gastos
        """
        user_name = user_data.get("usuario", {}).get("nome", "Usuário")
        main_goal = user_data.get("usuario", {}).get("meta_principal", "")

        prompt = ANALYSIS_PROMPT.format(
            user_name=user_name,
            period=period,
            financial_data=user_data,
            main_goal=main_goal
        )

        return self.ai_client.generate_structured_content(prompt)

    def generate_economy_report(self, user_data: dict[str, Any], period: str = "mês atual") -> dict[str, Any]:
        """Gera um relatório de redução de gastos.

        Args:
            user_data: Dados financeiros do usuário
            period: Período para análise

        Returns:
            Relatório detalhado de redução de gastos
        """
        user_name = user_data.get("usuario", {}).get("nome", "Usuário")
        main_goal = user_data.get("usuario", {}).get("meta_principal", "")
        current_balance = user_data.get("resumo_geral", {}).get("saldo_liquido_mes", 0)

        prompt = ECONOMY_REPORT_PROMPT.format(
            user_name=user_name,
            period=period,
            financial_data=user_data,
            main_goal=main_goal,
            current_balance=current_balance,
            categoria_foco_1="lazer_e_estilo_de_vida",
            categoria_foco_2="outros_gastos"
        )

        return self.ai_client.generate_structured_content(prompt)

    def generate_financial_diagnostic(self, user_data: dict[str, Any], period: str = "mês atual") -> dict[str, Any]:
        """Realiza um diagnóstico completo da saúde financeira.

        Args:
            user_data: Dados financeiros do usuário
            period: Período para análise

        Returns:
            Diagnóstico completo da saúde financeira
        """
        user_name = user_data.get("usuario", {}).get("nome", "Usuário")

        prompt = DIAGNOSTIC_PROMPT.format(
            user_name=user_name,
            period=period,
            financial_data=user_data,
            current_savings_rate=22.08,
            recommended_savings_rate=30,
            recommended_expense_reduction=1500,
            emergency_fund_percent=40,
            goals_percent=30,
            investment_percent=30,
            categoria_foco_1="lazer_e_estilo_de_vida",
            categoria_foco_2="outros_gastos"
        )

        return self.ai_client.generate_structured_content(prompt)

    def analyze_user_transactions(
        self,
        transactions: list[dict[str, Any]],
        period: str = "mês atual"
    ) -> dict[str, Any]:
        """Analisa transações individuais do usuário.

        Args:
            transactions: Lista de transações
            period: Período de análise

        Returns:
            Análise de transações
        """
        prompt = f"""
Analise as seguintes transações do usuário para o período {period}:
{json.dumps(transactions, ensure_ascii=False, indent=2)}

Forneça:
1. Total de gastos por categoria
2. Padrões de gasto por dia da semana
3. Transações fora do orçamento
4. Sugestões para reduzir gastos recorrentes
"""

        return self.ai_client.generate_structured_content(prompt)

    def suggest_optimization_strategies(
        self,
        user_data: dict[str, Any],
        priorities: list[str] | None = None
    ) -> dict[str, Any]:
        """Sugere estratégias de otimização financeira personalizadas.

        Args:
            user_data: Dados financeiros do usuário
            priorities: Lista de prioridades do usuário (ex: ["emergência", "investimento", "redução_gastos"])

        Returns:
            Estratégias de otimização
        """
        if priorities is None:
            priorities = ["emergência", "investimento", "redução_gastos"]

        prompt = f"""
Sugira estratégias de otimização financeira para {user_data.get("usuario", {}).get("nome", "Usuário")}
considerando estas prioridades: {', '.join(priorities)}

Dados financeiros:
{json.dumps(user_data, ensure_ascii=False, indent=2)}

Forneça estratégias concretas e acionáveis para cada prioridade.
"""

        return self.ai_client.generate_structured_content(prompt)
