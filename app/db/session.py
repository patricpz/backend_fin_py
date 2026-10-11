from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool
from app.core.config import settings

_is_test = settings.APP_ENV == "test"

_url = settings.get_database_url()

engine = create_async_engine(
    _url,
    echo=settings.APP_ENV == "development",
    connect_args={"ssl": "require"} if "neon.tech" in _url else {},
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

def get_database_url() -> str:
    return _url
