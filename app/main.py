from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings
from app.core.handlers import register_exception_handlers
from app.core.rate_limit import register_rate_limiter
from app.api.v1 import (
    auth,
    accounts,
    categories,
    transactions,
    recurrences,
    budgets,
    goals,
    reports,
    health,
    ai_assistant,
    notifications,
    push,
    expenses,
)
from app.db.base import Base


def _build_lifespan(engine):
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        from app.alerts.scheduler import start_scheduler, stop_scheduler
        start_scheduler()
        yield
        stop_scheduler()
        await engine.dispose()

    return lifespan


def create_app(engine=None) -> FastAPI:
    engine = engine or __import__("app.db.session", fromlist=["engine"]).engine

    app = FastAPI(
        title="Financeiro Pessoal API",
        description="Backend para controle financeiro pessoal",
        version="0.1.0",
        lifespan=_build_lifespan(engine),
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    register_rate_limiter(app)

    app.include_router(health.router)
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(accounts.router, prefix="/api/v1")
    app.include_router(categories.router, prefix="/api/v1")
    app.include_router(transactions.router, prefix="/api/v1")
    app.include_router(recurrences.router, prefix="/api/v1")
    app.include_router(budgets.router, prefix="/api/v1")
    app.include_router(goals.router, prefix="/api/v1")
    app.include_router(reports.router, prefix="/api/v1")
    app.include_router(ai_assistant.router, prefix="/api/v1")

    # Rotas sob /api/v1
    app.include_router(notifications.router, prefix="/api/v1")
    app.include_router(push.router, prefix="/api/v1")
    app.include_router(expenses.router, prefix="/api/v1")

    # Rotas sob a raiz / para atendimento estrito ao contrato fixo
    app.include_router(notifications.router)
    app.include_router(push.router)
    app.include_router(expenses.router)

    return app


app = create_app()