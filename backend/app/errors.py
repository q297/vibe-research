import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.context import current_trace_id
from app.contracts.common import ApiError, ErrorCode
from app.services.ports import BudgetExhausted

log = logging.getLogger("app.errors")

_STATUS_TO_CODE = {
    400: ErrorCode.BAD_REQUEST,
    401: ErrorCode.UNAUTHORIZED,
    403: ErrorCode.FORBIDDEN,
    404: ErrorCode.NOT_FOUND,
    422: ErrorCode.BAD_REQUEST,
    429: ErrorCode.RATE_LIMITED,
}

ERROR_RESPONSES = {status: {"model": ApiError} for status in (400, 401, 403, 404, 429, 500, 503)}


class AppError(Exception):
    def __init__(self, status: int, code: ErrorCode, message: str, details: dict | None = None):
        self.status = status
        self.code = code
        self.message = message
        self.details = details


def not_found(what: str) -> AppError:
    return AppError(404, ErrorCode.NOT_FOUND, f"{what} not found")


def _response(
    status: int, code: ErrorCode, message: str, details: dict | None = None
) -> JSONResponse:
    body = ApiError(code=code, message=message, trace_id=current_trace_id(), details=details)
    return JSONResponse(status_code=status, content=body.model_dump(mode="json"))


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError):
        return _response(exc.status, exc.code, exc.message, exc.details)

    @app.exception_handler(BudgetExhausted)
    async def _budget(_: Request, exc: BudgetExhausted):
        return _response(503, ErrorCode.BUDGET_EXHAUSTED, "Daily LLM budget is exhausted")

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException):
        code = _STATUS_TO_CODE.get(exc.status_code, ErrorCode.INTERNAL)
        return _response(exc.status_code, code, str(exc.detail))

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError):
        errors = [{"loc": e["loc"], "msg": e["msg"]} for e in exc.errors()]
        return _response(422, ErrorCode.BAD_REQUEST, "Validation failed", {"errors": errors})

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception):
        log.exception("unhandled error", exc_info=exc)
        return _response(500, ErrorCode.INTERNAL, "Internal error")
