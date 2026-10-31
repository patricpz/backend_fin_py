#!/usr/bin/env python3
"""Script to test the new installment (parcelada) functionality."""

from decimal import Decimal
from datetime import date
import calendar

from app.models.transaction import Transaction
from app.models.enums import TransactionType
from app.schemas.transaction import TransactionCreate, InstallmentPayRequest
from app.services.transaction_service import TransactionService
from pydantic import ValidationError


def test_progress_calculation():
    print("Testando cálculo de progresso...")

    # Mock de um Transaction com os novos campos
    tx = Transaction(
        user_id="test-user-id",
        conta_id="test-account-id",
        categoria_id="test-category-id",
        tipo=TransactionType.DESPESA,
        valor=Decimal("1000.00"),
        descricao="Tablet",
        data=date(2026, 8, 1),
        is_installment=True,
        installment_count=10,
        paid_installments=2,
        first_due_date=date(2026, 9, 1),
    )

    # Teste de helper
    assert TransactionService._add_months(date(2026, 9, 1), 2) == date(2026, 11, 1)
    assert TransactionService._add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)  # não bissexto

    # Teste de cálculo de progresso
    progress = TransactionService._calculate_installment_progress(tx)
    print(f"Progresso calculado: {progress}")
    assert progress["installment_amount"] == Decimal("100.00")
    assert progress["paid_amount"] == Decimal("200.00")
    assert progress["remaining_amount"] == Decimal("800.00")
    assert progress["remaining_installments"] == 8
    assert progress["progress_percent"] == 20
    assert progress["is_completed"] is False
    assert progress["next_due_date"] == date(2026, 11, 1)

    # Teste com todas as parcelas pagas
    tx.paid_installments = 10
    progress2 = TransactionService._calculate_installment_progress(tx)
    print(f"Progresso concluído: {progress2}")
    assert progress2["paid_amount"] == Decimal("1000.00")
    assert progress2["remaining_amount"] == Decimal("0.00")
    assert progress2["remaining_installments"] == 0
    assert progress2["progress_percent"] == 100
    assert progress2["is_completed"] is True
    assert progress2["next_due_date"] is None

    # Teste de valor não divisível (1000 / 3 = 333.33, última = 333.34)
    tx2 = Transaction(
        user_id="test-user-id",
        conta_id="test-account-id",
        categoria_id="test-category-id",
        tipo=TransactionType.DESPESA,
        valor=Decimal("1000.00"),
        descricao="Divisible",
        data=date(2026, 8, 1),
        is_installment=True,
        installment_count=3,
        paid_installments=2,
        first_due_date=date(2026, 9, 1),
    )
    progress3 = TransactionService._calculate_installment_progress(tx2)
    print(f"Progresso com 3 parcelas: {progress3}")
    assert progress3["installment_amount"] == Decimal("333.33")
    assert progress3["paid_amount"] == Decimal("666.66")
    assert progress3["remaining_amount"] == Decimal("333.34")
    assert progress3["remaining_installments"] == 1
    assert progress3["progress_percent"] == round((2 / 3) * 100)

    # Teste de não-installment (sem progresso)
    tx3 = Transaction(
        user_id="test-user-id",
        conta_id="test-account-id",
        categoria_id="test-category-id",
        tipo=TransactionType.DESPESA,
        valor=Decimal("100.00"),
        descricao="Normal",
        data=date(2026, 8, 1),
    )
    progress4 = TransactionService._calculate_installment_progress(tx3)
    print(f"Progresso não-installment: {progress4}")
    assert progress4["installment_amount"] is None
    assert progress4["is_completed"] is False
    assert progress4["next_due_date"] is None

    print("Todos os testes de progresso passaram.\n")


def test_validation():
    print("Testando validação de negócios...")

    import uuid
    dummy_acc = uuid.uuid4()
    dummy_cat = uuid.uuid4()

    # Não é installment (default)
    create1 = TransactionCreate(
        conta_id=dummy_acc,
        categoria_id=dummy_cat,
        tipo=TransactionType.DESPESA,
        valor=Decimal("100.00"),
        data=date(2026, 8, 1),
        descricao="Normal",
        is_installment=False,
        installment_count=None,
        paid_installments=0,
        first_due_date=None,
    )
    assert create1.is_installment is False

    # É installment, mas precisa de installment_count >= 2
    try:
        TransactionCreate(
            conta_id=dummy_acc,
            categoria_id=dummy_cat,
            tipo=TransactionType.DESPESA,
            valor=Decimal("100.00"),
            data=date(2026, 8, 1),
            descricao="Parcelada",
            is_installment=True,
            installment_count=1,  # Inválido
            paid_installments=0,
            first_due_date=date(2026, 9, 1),
        )
        print("ERROR: Deve ter falhado com installment_count < 2")
        assert False, "Deveria ter falhado com installment_count < 2"
    except ValidationError:
        print("Correto: Falha com installment_count < 2")

    # É installment, sem first_due_date (obrigatório)
    try:
        TransactionCreate(
            conta_id=dummy_acc,
            categoria_id=dummy_cat,
            tipo=TransactionType.DESPESA,
            valor=Decimal("100.00"),
            data=date(2026, 8, 1),
            descricao="Parcelada",
            is_installment=True,
            installment_count=2,
            paid_installments=0,
            first_due_date=None,  # Obrigatório
        )
        print("ERROR: Deve ter falhado sem first_due_date")
        assert False, "Deveria ter falhado sem first_due_date"
    except ValidationError:
        print("Correto: Falha sem first_due_date")

    print("Todos os testes de validação passaram.\n")


if __name__ == "__main__":
    print("=== Testes Manuais do Recurso de Parcelas ===\n")
    test_progress_calculation()
    test_validation()
    print("Todos os testes manuais passaram!")