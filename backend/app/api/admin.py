from fastapi import APIRouter, status

from app.api.deps import Svc
from app.auth import CurrentUser, UserRecord, ensure_client_access
from app.contracts.common import ErrorCode
from app.contracts.platform import WarmupRequest, WarmupStatus
from app.errors import AppError

router = APIRouter(prefix="/admin", tags=["admin"])


def _require_admin(user: UserRecord) -> None:
    if not user.is_demo_admin:
        raise AppError(403, ErrorCode.FORBIDDEN, "Available to the demo admin only")


@router.post("/warm-cache", response_model=WarmupStatus, status_code=status.HTTP_202_ACCEPTED)
async def start_warmup(body: WarmupRequest, user: CurrentUser, svc: Svc) -> WarmupStatus:
    _require_admin(user)
    if svc.warmup.status.running:
        raise AppError(409, ErrorCode.BAD_REQUEST, "Warm-up is already running")
    client_ids = body.client_ids or user.client_ids
    for client_id in client_ids:
        ensure_client_access(user, client_id)
    return svc.warmup.start(svc, body, client_ids, user.role)


@router.get("/warm-cache", response_model=WarmupStatus)
async def warmup_status(user: CurrentUser, svc: Svc) -> WarmupStatus:
    _require_admin(user)
    return svc.warmup.status
