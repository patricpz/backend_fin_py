from typing import Any

from pydantic import BaseModel


class AnalyzeExpensesRequest(BaseModel):
    """Request para análise de gastos."""
    user_data: dict[str, Any]
    period: str | None = "mês atual"


class EconomyReportRequest(BaseModel):
    """Request para relatório de economia."""
    user_data: dict[str, Any]
    period: str | None = "mês atual"


class FinancialDiagnosticRequest(BaseModel):
    """Request para diagnóstico financeiro."""
    user_data: dict[str, Any]
    period: str | None = "mês atual"


class OptimizeStrategiesRequest(BaseModel):
    """Request para estratégias de otimização."""
    user_data: dict[str, Any]
    priorities: list[str] | None = None


class FinancialAIResponse(BaseModel):
    """Resposta padrão do assistente de IA."""
    success: bool = True
    data: dict[str, Any]
    message: str | None = None