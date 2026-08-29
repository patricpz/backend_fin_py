from enum import Enum


class AccountType(str, Enum):
    CORRENTE = "corrente"
    POUPANCA = "poupanca"
    CARTEIRA = "carteira"
    INVESTIMENTO = "investimento"
    CARTAO_CREDITO = "cartao_credito"


class TransactionType(str, Enum):
    RECEITA = "receita"
    DESPESA = "despesa"
    TRANSFERENCIA = "transferencia"


class TransactionStatus(str, Enum):
    PENDENTE = "pendente"
    CONFIRMADO = "confirmado"


class CategoryType(str, Enum):
    RECEITA = "receita"
    DESPESA = "despesa"


class RecurrenceFrequency(str, Enum):
    DIARIA = "diaria"
    SEMANAL = "semanal"
    MENSAL = "mensal"
    ANUAL = "anual"


class BudgetAlertPercent(int, Enum):
    DEFAULT = 80


class GoalStatus(str, Enum):
    EM_ANDAMENTO = "em_andamento"
    CONCLUIDA = "concluida"
    CANCELADA = "cancelada"


class GoalContributionType(str, Enum):
    APORTE = "aporte"
    RETIRADA = "retirada"