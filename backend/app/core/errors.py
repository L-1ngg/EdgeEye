from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.models.responses import ApiErrorResponse, ErrorPayload


class ApiException(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details


def _error_response(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = ApiErrorResponse(
        error=ErrorPayload(code=code, message=message, details=details),
        timestamp=datetime.now(UTC),
    )
    return payload.model_dump(mode="json")


def _json_safe_errors(exc: RequestValidationError) -> list[dict[str, Any]]:
    safe_errors = []
    for error in exc.errors():
        safe_error = dict(error)
        if "ctx" in safe_error and isinstance(safe_error["ctx"], dict):
            safe_error["ctx"] = {
                key: value if isinstance(value, str | int | float | bool | type(None)) else str(value)
                for key, value in safe_error["ctx"].items()
            }
        safe_errors.append(safe_error)
    return safe_errors


async def api_exception_handler(_: Request, exc: ApiException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_response(exc.code, exc.message, exc.details),
    )


async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content=_error_response(
            "VALIDATION_ERROR",
            "invalid request payload",
            {"errors": _json_safe_errors(exc)},
        ),
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ApiException, api_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
