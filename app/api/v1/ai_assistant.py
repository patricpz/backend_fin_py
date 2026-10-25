from fastapi import APIRouter, Depends, HTTPException, status

from app.core.deps import get_current_user
from app.ia.ai_assistant import FinancialAIAssistant
from app.ia.schemas import (
    AnalyzeExpensesRequest,
    EconomyReportRequest,
    FinancialAIResponse,
    FinancialDiagnosticRequest,
    OptimizeStrategiesRequest,
)
from app.models.user import User

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/analyze-expenses", response_model=FinancialAIResponse, status_code=status.HTTP_200_OK)
async def analyze_expenses(
    data: AnalyzeExpensesRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Análise de Gastos
    ------------------
    Identifica padrões de consumo e categorias de maior impacto, sugerindo oportunidades de redução.

    - **user_data**: Dados financeiros do usuário (transações, categorias, etc.)
    - **period**: Período para análise (padrão: "mês atual")
    """
    try:
        service = FinancialAIAssistant()
        result = service.analyze_expenses(data.user_data, data.period)
        return FinancialAIResponse(success=True, data=result, message="Análise de gastos concluída")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro na análise: {str(e)}")


@router.post("/economy-report", response_model=FinancialAIResponse, status_code=status.HTTP_200_OK)
async def economy_report(
    data: EconomyReportRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Relatório de Redução de Gastos
    ------------------------------
    Gera um relatório detalhado sobre para onde reduzir os gastos, com plano de ação mensurável.

    - **user_data**: Dados financeiros do usuário
    - **period**: Período para análise (padrão: "mês atual")
    """
    try:
        service = FinancialAIAssistant()
        result = service.generate_economy_report(data.user_data, data.period)
        return FinancialAIResponse(
            success=True,
            data=result,
            message="Relatório de economia gerado com sucesso"
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro na geração do relatório: {str(e)}")


@router.post("/diagnostic", response_model=FinancialAIResponse, status_code=status.HTTP_200_OK)
async def financial_diagnostic(
    data: FinancialDiagnosticRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Diagnóstico Financeiro
    ----------------------
    Avalia a saúde financeira geral, identifica pontos fortes e fracos, e recomendações estratégicas.

    - **user_data**: Dados financeiros do usuário
    - **period**: Período para análise (padrão: "mês atual")
    """
    try:
        service = FinancialAIAssistant()
        result = service.generate_financial_diagnostic(data.user_data, data.period)
        return FinancialAIResponse(
            success=True,
            data=result,
            message="Diagnóstico financeiro gerado com sucesso"
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro no diagnóstico: {str(e)}")


@router.post("/strategies", response_model=FinancialAIResponse, status_code=status.HTTP_200_OK)
async def optimization_strategies(
    data: OptimizeStrategiesRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Estratégias de Otimização
    -------------------------
    Sugere estratégias de otimização financeira personalizadas por prioridade.

    - **user_data**: Dados financeiros do usuário
    - **priorities**: Lista de prioridades (padrão: ["emergência", "investimento", "redução_gastos"])
    """
    try:
        service = FinancialAIAssistant()
        result = service.suggest_optimization_strategies(data.user_data, data.priorities)
        return FinancialAIResponse(
            success=True,
            data=result,
            message="Estratégias de otimização geradas com sucesso"
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro na geração de estratégias: {str(e)}")


@router.post("/analyze-transactions", response_model=FinancialAIResponse, status_code=status.HTTP_200_OK)
async def analyze_transactions(
    data: AnalyzeExpensesRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Análise de Transações
    ---------------------
    Analisa transações individuais para identificar padrões e oportunidades.

    - **user_data**: Dados financeiros do usuário
    - **period**: Período para análise (padrão: "mês atual")
    """
    try:
        service = FinancialAIAssistant()
        result = service.analyze_user_transactions(data.user_data.get("transacoes", []), data.period)
        return FinancialAIResponse(
            success=True,
            data=result,
            message="Análise de transações concluída"
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro na análise de transações: {str(e)}")
