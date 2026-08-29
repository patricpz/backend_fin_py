from typing import Optional
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base import BaseRepository
from app.models.user import User


class UserRepository(BaseRepository[User]):
    def __init__(self, db: AsyncSession):
        super().__init__(User, db)

    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self.db.execute(select(User).where(func.lower(User.email) == func.lower(email)))
        return result.scalar_one_or_none()

    async def get_by_id(self, id: UUID) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.id == id, User.ativo == True))
        return result.scalar_one_or_none()