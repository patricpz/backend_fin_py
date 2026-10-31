import asyncio
import pytest
import pytest_asyncio
from typing import AsyncGenerator

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

from app.main import create_app
from app.db.base import Base
from app.core.security import hash_password
from app.models import (
    User,
    Account,
    Category,
    Transaction,
    RecurringTransaction,
    Budget,
    Goal,
    GoalContribution,
    RefreshToken,
    Installment,
)


def _ensure_all_models_registered() -> None:
    from app.models import (
        User,
        Account,
        Category,
        Transaction,
        RecurringTransaction,
        Budget,
        Goal,
        GoalContribution,
        RefreshToken,
        Installment,
        Notification,
        NotificationPreference,
        PushSubscription,
        NotificationFeedback,
    )
    package_models = (
        User,
        Account,
        Category,
        Transaction,
        RecurringTransaction,
        Budget,
        Goal,
        GoalContribution,
        RefreshToken,
        Installment,
        Notification,
        NotificationPreference,
        PushSubscription,
        NotificationFeedback,
    )
    for model in package_models:
        if not hasattr(model, "__table__"):
            raise AssertionError(f"Modelo {model.__name__} não possui __table__")

    Base.metadata.reflect = False
    assert "installments" in Base.metadata.tables, "Tabela 'installments' não está registrada no metadata de teste"


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def test_engine() -> AsyncSession:
    _ensure_all_models_registered()
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(test_engine: AsyncSession) -> AsyncGenerator[AsyncSession, None]:
    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@pytest_asyncio.fixture(scope="function")
async def client(test_engine: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app = create_app(engine=test_engine)
    app.dependency_overrides.clear()
    app.dependency_overrides[__import__("app.db.session", fromlist=["get_db"]).get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture(scope="function")
async def test_user(db_session: AsyncSession) -> User:
    user = User(
        nome="Test User",
        email="test@example.com",
        senha_hash=hash_password("testpass123"),
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
async def auth_headers(test_user: User) -> dict[str, str]:
    from app.core.security import create_access_token

    token = create_access_token({"sub": str(test_user.id), "type": "access"})
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
