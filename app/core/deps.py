from typing import AsyncGenerator, Optional
from fastapi import Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import jwt, JWTError

from app.db.session import get_db, async_session_maker
from app.core.config import settings
from app.core.security import decode_token, get_token_type
from app.core.exceptions import UnauthorizedError, ForbiddenError
from app.models.user import User


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = decode_token(token)
        if get_token_type(payload) != "access":
            raise UnauthorizedError("Token inválido", "INVALID_TOKEN_TYPE")
        user_id: str = payload.get("sub")
        if not user_id:
            raise UnauthorizedError("Token inválido", "INVALID_TOKEN_PAYLOAD")
    except ValueError as e:
        raise UnauthorizedError(str(e), "INVALID_TOKEN")

    result = await db.execute(select(User).where(User.id == user_id, User.ativo == True))
    user = result.scalar_one_or_none()
    if not user:
        raise UnauthorizedError("Usuário não encontrado", "USER_NOT_FOUND")
    return user


async def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    if not token:
        return None
    try:
        return await get_current_user(token, db)
    except (UnauthorizedError, ForbiddenError):
        return None


class PaginationParams:
    def __init__(
        self,
        page: int = Query(1, ge=1, description="Número da página"),
        size: int = Query(20, ge=1, le=100, description="Itens por página"),
    ):
        self.page = page
        self.size = size
        self.offset = (page - 1) * size
        self.limit = size