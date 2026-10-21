"""Request-scoped trace id (J1) and the call log (H4)"""

import json
import logging
import time
import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

TRACE_HEADER = "X-Trace-Id"

_trace_id: ContextVar[str | None] = ContextVar("trace_id", default=None)
call_log = logging.getLogger("app.calls")


def current_trace_id() -> str | None:
    return _trace_id.get()


def new_trace_id() -> str:
    return f"tr-{uuid.uuid4().hex[:16]}"


class TraceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        incoming = request.headers.get(TRACE_HEADER, "")
        trace_id = (
            incoming if incoming.startswith("tr-") and len(incoming) <= 64 else new_trace_id()
        )
        token = _trace_id.set(trace_id)
        started = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers[TRACE_HEADER] = trace_id
            return response
        finally:
            # Only metadata goes to the log, never request bodies with user text
            call_log.info(
                json.dumps(
                    {
                        "trace_id": trace_id,
                        "method": request.method,
                        "path": request.url.path,
                        "status": status,
                        "duration_ms": round((time.perf_counter() - started) * 1000),
                    }
                )
            )
            _trace_id.reset(token)
