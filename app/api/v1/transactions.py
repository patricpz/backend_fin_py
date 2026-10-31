from fastapi import APIRouter, Depends, status, Header, Body
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional
from app.db.session import get_db
from app.core.deps import get_current_user, PaginationParams
from app.schemas.transaction import (
    TransactionCreate,
    TransactionUpdate,
    TransactionResponse,
    TransactionResponseWithInstallments,
    TransactionFilters,
    InstallmentPayRequest,
    TransactionInstallmentResponse,
    InstallmentsSummaryResponse,
)
from app.schemas.installment import InstallmentCreate, InstallmentResponse
from app.services.transaction_service import TransactionService
from app.schemas.common import Page
from app.models.user import User
from app.models.enums import TransactionType, TransactionStatus as TS


router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post("", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    data: TransactionCreate,
    idempotency_key: Optional[UUID] = Header(None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = TransactionService(db)
    if idempotency_key:
        data.idempotency_key = idempotency_key
    transaction = await service.create(current_user.id, data)
    # Anexa progresso se for despesa parcelada
    if transaction.is_installment:
        service._attach_progress(transaction)
    return transaction


@router.get("", response_model=Page[TransactionResponse])
async def list_transactions(
    filters: TransactionFilters = Depends(),
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = TransactionService(db)
    transactions, total = await service.list(current_user.id, filters, pagination.page, pagination.size)
    # Anexa progresso para qualquer transação parcelada na lista
    for tx in transactions:
        if tx.is_installment:
            service._attach_progress(tx)
    return Page.create(transactions, total, pagination.page, pagination.size)


@router.get("/installments", response_model=Page[TransactionInstallmentResponse])
async def list_installments(
    filters: TransactionFilters = Depends(),
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lista despesas parceladas do usuário autenticado com progresso de pagamento."""
    service = TransactionService(db)
    transactions, total = await service.list_installments(current_user.id, filters, pagination.page, pagination.size)
    return Page.create(transactions, total, pagination.page, pagination.size)


@router.get("/installments/summary", response_model=InstallmentsSummaryResponse)
async def get_installments_summary(
    filters: TransactionFilters = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retorna métricas consolidadas dos parcelamentos do usuário (cards de dashboard)."""
    service = TransactionService(db)
    return await service.get_installments_summary(current_user.id, filters)


@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(transaction_id: UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = TransactionService(db)
    transaction = await service.get(current_user.id, transaction_id)
    if transaction.is_installment:
        service._attach_progress(transaction)
    return transaction


@router.patch("/{transaction_id}", response_model=TransactionResponse)
async def update_transaction(transaction_id: UUID, data: TransactionUpdate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = TransactionService(db)
    return await service.update(current_user.id, transaction_id, data)


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(transaction_id: UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = TransactionService(db)
    await service.delete(current_user.id, transaction_id)


@router.post("/{transaction_id}/confirm", response_model=TransactionResponse)
async def confirm_transaction(transaction_id: UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = TransactionService(db)
    return await service.confirm(current_user.id, transaction_id)


@router.patch("/{transaction_id}/pay", response_model=TransactionInstallmentResponse)
async def pay_installment(
    transaction_id: UUID,
    payload: Optional[InstallmentPayRequest] = Body(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Registra pagamento de uma parcela (incrementa paid_installments).

    Body opcional: { "paidInstallments": n } para correção manual, ou omitido/vazio para pagar a próxima parcela.
    """
    service = TransactionService(db)
    transaction = await service.pay_installment(current_user.id, transaction_id, payload)
    service._attach_progress(transaction)
    return transaction


@router.post("/{transaction_id}/parcelar", response_model=TransactionResponseWithInstallments)
async def parcelar_transacao(
    transaction_id: UUID,
    data: InstallmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = TransactionService(db)
    transaction = await service.parcelar(current_user.id, transaction_id, data)
    # Recarrega com installments para resposta
    transaction = await service.tx_repo.get_by_id_with_installments(transaction_id, current_user.id)
    installments_data = [
        InstallmentResponse(
            id=i.id,
            transaction_id=i.transaction_id,
            parcela_numero=i.parcela_numero,
            valor=i.valor,
            data_vencimento=i.data_vencimento,
            status=i.status.value,
            observacoes=i.observacoes,
        )
        for i in (transaction.installments or [])
    ]
    return TransactionResponseWithInstallments(
        id=transaction.id,
        user_id=transaction.user_id,
        conta_id=transaction.conta_id,
        conta_destino_id=transaction.conta_destino_id,
        categoria_id=transaction.categoria_id,
        tipo=TransactionType(transaction.tipo),
        valor=transaction.valor,
        data=transaction.data,
        descricao=transaction.descricao,
        observacoes=transaction.observacoes,
        status=TS(transaction.status),
        anexo_url=transaction.anexo_url,
        recorrencia_id=transaction.recorrencia_id,
        idempotency_key=transaction.idempotency_key,
        criado_em=transaction.criado_em,
        atualizado_em=transaction.atualizado_em,
        installments_total_count=transaction.installments_total_count,
        installments=installments_data,
    )


@router.get("/{transaction_id}/parcelas", response_model=list[InstallmentResponse])
async def listar_parcelas(
    transaction_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = TransactionService(db)
    return await service.get_installments(current_user.id, transaction_id)