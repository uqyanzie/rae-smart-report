"""Unified JSON error envelopes for the REST API."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse

from app.modules.ingestion.exceptions import (
    IngestionError,
    InvalidSpreadsheetError,
    MissingRequiredColumnError,
    SheetNotFoundError,
    SpreadsheetEmptyError,
    UnsupportedFormatError,
)
from app.modules.transformer.errors import InvalidVariantError

__all__ = ["error_response", "register_exception_handlers"]


def error_response(
    status: int,
    code: str,
    message: str,
    details: Any | None = None,
) -> JSONResponse:
    """Builds the canonical error envelope: ``{status, code, message, details}``."""
    body: dict[str, Any] = {
        "status": "error",
        "code": code,
        "message": message,
    }
    if details is not None:
        body["details"] = details
    return JSONResponse(status_code=status, content=body)


_INGESTION_ERROR_MAP: dict[type[IngestionError], tuple[int, str]] = {
    UnsupportedFormatError: (415, "UNSUPPORTED_FORMAT"),
    SheetNotFoundError: (404, "SHEET_NOT_FOUND"),
    MissingRequiredColumnError: (422, "MISSING_REQUIRED_COLUMN"),
    SpreadsheetEmptyError: (422, "EMPTY_SPREADSHEET"),
    InvalidSpreadsheetError: (422, "INVALID_SPREADSHEET"),
}


def register_exception_handlers(app: FastAPI) -> None:
    """Registers app-wide exception handlers producing camelCase envelopes."""

    @app.exception_handler(IngestionError)
    async def _handle_ingestion_error(request: Request, exc: IngestionError) -> JSONResponse:
        status, code = _INGESTION_ERROR_MAP.get(type(exc), (400, "INGESTION_ERROR"))
        return error_response(status, code, str(exc))

    @app.exception_handler(InvalidVariantError)
    async def _handle_invalid_variant(
        request: Request, exc: InvalidVariantError
    ) -> JSONResponse:
        return error_response(422, "INVALID_VARIANT", str(exc))

    @app.exception_handler(StarletteHTTPException)
    async def _handle_http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return error_response(exc.status_code, "HTTP_ERROR", str(exc.detail))

    @app.exception_handler(RequestValidationError)
    async def _handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        return error_response(
            422,
            "VALIDATION_ERROR",
            "Request validation failed",
            details=jsonable_encoder(exc.errors()),
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        return error_response(500, "INTERNAL_ERROR", f"Internal server error: {exc}")
