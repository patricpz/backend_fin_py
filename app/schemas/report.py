from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from uuid import UUID
from datetime import date
from decimal import Decimal


class MonthlySummary(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mes: int
    ano: int
    total_receitas: Decimal
    total_despesas: Decimal
    saldo: Decimal
    total_transferencias_enviadas: Decimal
    total_transferencias_recebidas: Decimal


class CategorySpending(BaseModel):
    model_config = ConfigDict(extra="forbid")
    categoria_id: UUID
    categoria_nome: str
    cor: str
    icone: str
    valor: Decimal
    percentual: float
    tipo: str


class CategorySpendingReport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mes: int
    ano: int
    total_despesas: Decimal
    categorias: List[CategorySpending]


class BalanceEvolutionPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")
    data: date
    saldo: Decimal


class BalanceEvolutionReport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    conta_id: UUID
    conta_nome: str
    pontos: List[BalanceEvolutionPoint]


class BudgetVsActual(BaseModel):
    model_config = ConfigDict(extra="forbid")
    categoria_id: UUID
    categoria_nome: str
    orcado: Decimal
    realizado: Decimal
    percentual: float
    alerta: bool


class BudgetVsActualReport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mes: int
    ano: int
    orcamentos: List[BudgetVsActual]