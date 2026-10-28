from fastapi import Request, FastAPI
from fastapi.responses import JSONResponse
from app.core.exceptions import AppError
from sqlalchemy.exc import IntegrityError
from pydantic import ValidationError as PydanticValidationError
from http import HTTPStatus
from datetime import datetime, timezone


def _build_error_payload(status_code: int, message: str, code: str) -> dict:
    try:
        phrase = HTTPStatus(status_code).phrase
    except ValueError:
        phrase = "Error"
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    return {
        "statusCode": status_code,
        "error": phrase,
        "message": message,
        "timestamp": now_iso,
        "detail": message,
        "code": code,
    }


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        return JSONResponse(
            status_code=exc.status_code,
            content=_build_error_payload(exc.status_code, exc.detail, exc.code),
        )

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(request: Request, exc: IntegrityError):
        return JSONResponse(
            status_code=409,
            content=_build_error_payload(409, "Violação de integridade dos dados", "INTEGRITY_ERROR"),
        )

    @app.exception_handler(PydanticValidationError)
    async def pydantic_validation_error_handler(request: Request, exc: PydanticValidationError):
        return JSONResponse(
            status_code=422,
            content=_build_error_payload(422, str(exc), "VALIDATION_ERROR"),
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content=_build_error_payload(500, "Erro interno do servidor", "INTERNAL_ERROR"),
        )
