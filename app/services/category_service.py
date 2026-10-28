from __future__ import annotations

from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.category import Category
from app.repositories.category_repository import CategoryRepository
from app.schemas.category import CategoryCreate, CategoryUpdate, CategoryTree
from app.core.exceptions import NotFoundError, BusinessRuleError, ConflictError


class CategoryService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = CategoryRepository(db)

    async def create(self, user_id: UUID, data: CategoryCreate) -> Category:
        if data.categoria_pai_id:
            parent = await self.repo.get_by_id(data.categoria_pai_id, user_id)
            if not parent:
                raise NotFoundError("Categoria pai não encontrada", "PARENT_CATEGORY_NOT_FOUND")
            if parent.tipo != data.tipo:
                raise BusinessRuleError("Categoria pai deve ser do mesmo tipo", "INVALID_PARENT_TYPE")

        existing = await self.repo.get_by_name_and_type(user_id, data.nome, data.tipo)
        if existing:
            raise ConflictError("Category with this name already exists for this user", "CATEGORY_EXISTS")

        category = Category(
            user_id=user_id,
            nome=data.nome,
            tipo=data.tipo,
            cor=data.cor,
            icone=data.icone,
            categoria_pai_id=data.categoria_pai_id,
        )
        self.db.add(category)
        await self.db.flush()
        await self.db.refresh(category)
        return category

    async def get(self, user_id: UUID, category_id: UUID) -> Category:
        category = await self.repo.get_by_id(category_id, user_id)
        if not category:
            raise NotFoundError("Categoria não encontrada", "CATEGORY_NOT_FOUND")
        return category

    async def list(
        self,
        user_id: UUID,
        tipo: str | None = None,
        page: int = 1,
        size: int = 100,
        ativo_only: bool | None = True,
    ):
        categories = await self.repo.get_by_user(user_id, tipo, ativo_only, size, (page - 1) * size)
        total = await self.repo.count_by_user(user_id, tipo, ativo_only)
        return categories, total

    async def get_tree(self, user_id: UUID, tipo: str | None = None) -> list[CategoryTree]:
        root_cats = await self.repo.get_tree(user_id, tipo)
        return [await self._build_tree(cat) for cat in root_cats]

    async def _build_tree(self, category: Category) -> CategoryTree:
        children = await self.repo.get_children(category.user_id, category.id)
        return CategoryTree(
            id=category.id,
            user_id=category.user_id,
            nome=category.nome,
            tipo=category.tipo,
            cor=category.cor,
            icone=category.icone,
            categoria_pai_id=category.categoria_pai_id,
            ativo=category.ativo,
            criado_em=category.criado_em,
            atualizado_em=category.atualizado_em,
            children=[await self._build_tree(c) for c in children]
        )

    async def update(self, user_id: UUID, category_id: UUID, data: CategoryUpdate) -> Category:
        category = await self.get(user_id, category_id)
        update_data = data.model_dump(exclude_unset=True)
        if "categoria_pai_id" in update_data and update_data["categoria_pai_id"]:
            parent = await self.repo.get_by_id(update_data["categoria_pai_id"], user_id)
            if not parent:
                raise NotFoundError("Categoria pai não encontrada", "PARENT_CATEGORY_NOT_FOUND")
            if parent.tipo != category.tipo:
                raise BusinessRuleError("Categoria pai deve ser do mesmo tipo", "INVALID_PARENT_TYPE")
            if parent.id == category_id:
                raise BusinessRuleError("Categoria não pode ser pai de si mesma", "SELF_PARENT")
        for field, value in update_data.items():
            setattr(category, field, value)
        await self.db.flush()
        await self.db.refresh(category)
        return category

    async def delete(self, user_id: UUID, category_id: UUID, migrar_para_id: UUID | None = None) -> bool:
        category = await self.get(user_id, category_id)
        tx_count = await self.repo.count_transactions(category_id)

        if tx_count > 0:
            if not migrar_para_id:
                raise ConflictError(
                    "Category has transactions. Provide migrar_para_id to reassign before deletion.",
                    "CATEGORY_HAS_TRANSACTIONS",
                )
            if migrar_para_id == category_id:
                raise BusinessRuleError("Cannot migrate category to itself", "SELF_MIGRATION")
            target = await self.repo.get_by_id(migrar_para_id, user_id)
            if not target:
                raise NotFoundError("Categoria de destino não encontrada", "MIGRATION_CATEGORY_NOT_FOUND")
            if target.tipo != category.tipo:
                raise BusinessRuleError("Categoria de destino deve ser do mesmo tipo", "INVALID_PARENT_TYPE")

            await self.repo.reassign_transactions(category_id, migrar_para_id, user_id)
            await self.repo.reassign_recurring(category_id, migrar_para_id, user_id)

        await self.repo.detach_children(category_id, user_id)
        await self.repo.delete_budgets(category_id, user_id)
        await self.repo.delete(category)
        return True
