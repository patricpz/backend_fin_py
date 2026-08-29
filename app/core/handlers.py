from fastapi import Request, FastAPI
from fastapi.responses import JSONResponse
from app.core.exceptions import AppError
from sqlalchemy.exc import IntegrityError
from pydantic import ValidationError as PydanticValidationError


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "code": exc.code},
        )

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(request: Request, exc: IntegrityError):
        return JSONResponse(
            status_code=409,
            content={"detail": "Violação de integridade dos dados", "code": "INTEGRITY_ERROR"},
        )

    @app.exception_handler(PydanticValidationError)
    async def pydantic_validation_error_handler(request: Request, exc: PydanticValidationError):
        return JSONResponse(
            status_code=422,
            content={"detail": str(exc), "code": "VALIDATION_ERROR"},
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={"detail": "Erro interno do servidor", "code": "INTERNAL_ERROR"},
        )