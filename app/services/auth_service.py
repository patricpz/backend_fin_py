from datetime import timedelta
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User
from app.models.refresh_token import RefreshToken
from app.repositories.user_repository import UserRepository
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token
from app.core.exceptions import UnauthorizedError, ConflictError
from app.schemas.auth import UserRegister, UserLogin, TokenResponse, RefreshTokenRequest
import uuid


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)

    async def register(self, data: UserRegister) -> User:
        existing = await self.user_repo.get_by_email(data.email)
        if existing:
            raise ConflictError("Email já cadastrado", "EMAIL_EXISTS")

        user = User(
            nome=data.nome,
            email=data.email,
            senha_hash=hash_password(data.senha),
        )
        self.db.add(user)
        await self.db.flush()
        await self.seed_default_categories(user.id)
        return user

    async def login(self, data: UserLogin) -> TokenResponse:
        user = await self.user_repo.get_by_email(data.email)
        if not user or not verify_password(data.senha, user.senha_hash):
            raise UnauthorizedError("Credenciais inválidas", "INVALID_CREDENTIALS")
        if not user.ativo:
            raise UnauthorizedError("Usuário inativo", "USER_INACTIVE")

        jti = str(uuid.uuid4())
        access_token = create_access_token({"sub": str(user.id)})
        refresh_token = create_refresh_token({"sub": str(user.id)}, jti=jti)

        rt = RefreshToken(
            user_id=user.id,
            jti=jti,
            expira_em=None,
            revogado=False,
        )
        self.db.add(rt)
        await self.db.flush()

        return TokenResponse(access_token=access_token, refresh_token=refresh_token)

    async def refresh(self, request: RefreshTokenRequest) -> TokenResponse:
        from app.core.security import decode_token, get_token_type
        try:
            payload = decode_token(request.refresh_token)
            if get_token_type(payload) != "refresh":
                raise UnauthorizedError("Token inválido", "INVALID_TOKEN_TYPE")
            user_id = UUID(payload.get("sub"))
            jti = payload.get("jti")
            if not jti:
                raise UnauthorizedError("Token inválido", "MISSING_JTI")
        except ValueError as e:
            raise UnauthorizedError(str(e), "INVALID_TOKEN")

        result = await self.db.execute(select(RefreshToken).where(RefreshToken.user_id == user_id, RefreshToken.jti == jti))
        rt = result.scalar_one_or_none()
        if not rt or rt.revogado:
            raise UnauthorizedError("Token revogado ou inválido", "TOKEN_REVOKED")

        new_jti = str(uuid.uuid4())
        new_access = create_access_token({"sub": str(user_id)})
        new_refresh = create_refresh_token({"sub": str(user_id)}, jti=new_jti)

        rt.revogado = True
        new_rt = RefreshToken(user_id=user_id, jti=new_jti, expira_em=None, revogado=False)
        self.db.add(new_rt)
        await self.db.flush()

        return TokenResponse(access_token=new_access, refresh_token=new_refresh)

    async def logout(self, user_id: UUID) -> None:
        await self.db.execute(
            RefreshToken.__table__.update().where(RefreshToken.user_id == user_id).values(revogado=True)
        )

    async def seed_default_categories(self, user_id: UUID) -> None:
        from app.models.category import Category
        from app.models.enums import CategoryType

        defaults = [
            # Despesas
            {"nome": "Alimentação", "tipo": CategoryType.DESPESA, "cor": "#EF4444", "icone": "utensils"},
            {"nome": "Transporte", "tipo": CategoryType.DESPESA, "cor": "#3B82F6", "icone": "car"},
            {"nome": "Moradia", "tipo": CategoryType.DESPESA, "cor": "#8B5CF6", "icone": "home"},
            {"nome": "Lazer", "tipo": CategoryType.DESPESA, "cor": "#EC4899", "icone": "gamepad-2"},
            {"nome": "Saúde", "tipo": CategoryType.DESPESA, "cor": "#10B981", "icone": "heart-pulse"},
            {"nome": "Educação", "tipo": CategoryType.DESPESA, "cor": "#F59E0B", "icone": "graduation-cap"},
            {"nome": "Outros", "tipo": CategoryType.DESPESA, "cor": "#6B7280", "icone": "tag"},
            # Receitas
            {"nome": "Salário", "tipo": CategoryType.RECEITA, "cor": "#22C55E", "icone": "briefcase"},
            {"nome": "Investimentos", "tipo": CategoryType.RECEITA, "cor": "#14B8A6", "icone": "trending-up"},
            {"nome": "Outras Receitas", "tipo": CategoryType.RECEITA, "cor": "#84CC16", "icone": "plus-circle"},
        ]

        for cat in defaults:
            category = Category(user_id=user_id, **cat)
            self.db.add(category)

        await self.db.flush()