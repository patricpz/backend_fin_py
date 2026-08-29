from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool
from app.core.config import settings


_is_test = settings.APP_ENV == "test"

engine = create_async_engine(
    settings.get_database_url(),
    echo=settings.APP_ENV == "development",
    connect_args={"ssl": "require"} if "neon.tech" in settings.get_database_url() else {},
    poolclass=NullPool if _is_test else None,
    pool_pre_ping=not _is_test,
    pool_recycle=1800,
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncSession:
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()