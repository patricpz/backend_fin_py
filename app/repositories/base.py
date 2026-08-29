from typing import Generic, TypeVar, Optional, Sequence
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import DeclarativeBase

T = TypeVar("T", bound=DeclarativeBase)


class BaseRepository(Generic[T]):
    def __init__(self, model: type[T], db: AsyncSession):
        self.model = model
        self.db = db

    async def get_by_id(self, id: UUID) -> Optional[T]:
        result = await self.db.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def get_all(
        self, 
        user_id: Optional[UUID] = None, 
        offset: int = 0, 
        limit: int = 100
    ) -> Sequence[T]:
        query = select(self.model)
        
        # Filtra por user_id apenas se o parâmetro for passado e o model possuir o atributo
        if user_id is not None and hasattr(self.model, "user_id"):
            query = query.where(self.model.user_id == user_id)
            
        query = query.offset(offset).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def count(self) -> int:
        result = await self.db.execute(select(func.count()).select_from(self.model))
        return result.scalar_one()

    async def create(self, obj: T) -> T:
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def update(self, obj: T) -> T:
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def delete(self, obj: T) -> None:
        await self.db.delete(obj)
        await self.db.flush()

    async def soft_delete(self, obj: T) -> T:
        if hasattr(obj, "ativo"):
            setattr(obj, "ativo", False)
            await self.db.flush()
            await self.db.refresh(obj)
            return obj
        raise AttributeError(f"O modelo '{self.model.__name__}' não possui o atributo 'ativo' para exclusão lógica.")