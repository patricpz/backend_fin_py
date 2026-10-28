from pydantic import BaseModel, ConfigDict, computed_field
from typing import List
from uuid import UUID
from datetime import date
from decimal import Decimal


class MonthlySummary(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)
    mes: int
    ano: int
    total_receitas: Decimal
    total_despesas: Decimal
    saldo: Decimal
    total_transferencias_enviadas: Decimal
    total_transferencias_recebidas: Decimal

    @computed_field
    @property
    def month(self) -> int:
        return self.mes

    @computed_field
    @property
    def year(self) -> int:
        return self.ano

    @computed_field
    @property
    def totalIncome(self) -> Decimal:
        return self.total_receitas

    @computed_field
    @property
    def totalExpenses(self) -> Decimal:
        return self.total_despesas

    @computed_field
    @property
    def balance(self) -> Decimal:
        return self.saldo

    @computed_field
    @property
    def totalTransfersSent(self) -> Decimal:
        return self.total_transferencias_enviadas

    @computed_field
    @property
    def totalTransfersReceived(self) -> Decimal:
        return self.total_transferencias_recebidas


class CategorySpending(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)
    categoria_id: UUID
    categoria_nome: str
    cor: str
    icone: str
    valor: Decimal
    percentual: float
    tipo: str

    @computed_field
    @property
    def categoryId(self) -> UUID:
        return self.categoria_id

    @computed_field
    @property
    def categoryName(self) -> str:
        return self.categoria_nome

    @computed_field
    @property
    def color(self) -> str:
        return self.cor

    @computed_field
    @property
    def icon(self) -> str:
        return self.icone

    @computed_field
    @property
    def amount(self) -> Decimal:
        return self.valor

    @computed_field
    @property
    def percentage(self) -> float:
        return self.percentual

    @computed_field
    @property
    def type(self) -> str:
        return self.tipo


class CategorySpendingReport(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)
    mes: int
    ano: int
    total_despesas: Decimal
    categorias: List[CategorySpending]

    @computed_field
    @property
    def month(self) -> int:
        return self.mes

    @computed_field
    @property
    def year(self) -> int:
        return self.ano

    @computed_field
    @property
    def total(self) -> Decimal:
        return self.total_despesas

    @computed_field
    @property
    def items(self) -> List[CategorySpending]:
        return self.categorias


class BalanceEvolutionPoint(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)
    data: date
    saldo: Decimal

    @computed_field
    @property
    def date(self) -> date:
        return self.data

    @computed_field
    @property
    def balance(self) -> Decimal:
        return self.saldo


class BalanceEvolutionReport(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)
    conta_id: UUID
    conta_nome: str
    pontos: List[BalanceEvolutionPoint]

    @computed_field
    @property
    def accountId(self) -> UUID:
        return self.conta_id

    @computed_field
    @property
    def accountName(self) -> str:
        return self.conta_nome

    @computed_field
    @property
    def points(self) -> List[BalanceEvolutionPoint]:
        return self.pontos


class MonthlyBalanceEvolution(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)
    mes: int
    ano: int
    total_receitas: Decimal
    total_despesas: Decimal
    saldo: Decimal

    @computed_field
    @property
    def month(self) -> int:
        return self.mes

    @computed_field
    @property
    def year(self) -> int:
        return self.ano

    @computed_field
    @property
    def totalIncome(self) -> Decimal:
        return self.total_receitas

    @computed_field
    @property
    def totalExpenses(self) -> Decimal:
        return self.total_despesas

    @computed_field
    @property
    def balance(self) -> Decimal:
        return self.saldo


class BudgetVsActual(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)
    categoria_id: UUID
    categoria_nome: str
    orcado: Decimal
    realizado: Decimal
    diferenca: Decimal
    percentual: float
    alerta: bool

    @computed_field
    @property
    def categoryId(self) -> UUID:
        return self.categoria_id

    @computed_field
    @property
    def categoryName(self) -> str:
        return self.categoria_nome

    @computed_field
    @property
    def budgeted(self) -> Decimal:
        return self.orcado

    @computed_field
    @property
    def actual(self) -> Decimal:
        return self.realizado

    @computed_field
    @property
    def difference(self) -> Decimal:
        return self.diferenca

    @computed_field
    @property
    def percentage(self) -> float:
        return self.percentual

    @computed_field
    @property
    def alert(self) -> bool:
        return self.alerta


class BudgetVsActualReport(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)
    mes: int
    ano: int
    orcamentos: List[BudgetVsActual]

    @computed_field
    @property
    def month(self) -> int:
        return self.mes

    @computed_field
    @property
    def year(self) -> int:
        return self.ano

    @computed_field
    @property
    def items(self) -> List[BudgetVsActual]:
        return self.orcamentos
