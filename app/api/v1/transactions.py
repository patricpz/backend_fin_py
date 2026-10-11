from fastapi import APIRouter, Depends, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional
from app.db.session import get_db
from app.core.deps import get_current_user, PaginationParams
from app.schemas.transaction import TransactionCreate, TransactionUpdate, TransactionResponse, TransactionResponseWithInstallments, TransactionFilters
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
    return await service.create(current_user.id, data)


@router.get("", response_model=Page[TransactionResponse])
async def list_transactions(
    filters: TransactionFilters = Depends(),
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = TransactionService(db)
    transactions, total = await service.list(current_user.id, filters, pagination.page, pagination.size)
    return Page.create(transactions, total, pagination.page, pagination.size)


@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(transaction_id: UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = TransactionService(db)
    return await service.get(current_user.id, transaction_id)


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