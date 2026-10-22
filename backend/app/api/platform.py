from fastapi import APIRouter, Request

from app.api.deps import Cfg, Svc
from app.auth import CurrentUser, authenticate, issue_token
from app.contracts.common import ErrorCode
from app.contracts.platform import Budget, Health, LoginRequest, Me, Metrics, Token
from app.errors import AppError

router = APIRouter(tags=["platform"])


@router.get("/health", response_model=Health)
async def health(settings: Cfg) -> Health:
    return Health(
        status="ok",
        mock_mode=settings.mock_mode,
        offline_mode=settings.offline_mode,
        version=settings.app_version,
    )


@router.post("/auth/login", response_model=Token)
async def login(body: LoginRequest, request: Request, svc: Svc, settings: Cfg) -> Token:
    # Only failures count and only per IP: a per-account lock would let anyone block "demo"
    ip = request.client.host if request.client else "unknown"
    svc.limiter.ensure_below(ip, "login_failure", settings.rate_limit_login_failures_per_hour)
    user = authenticate(body.username, body.password)
    if user is None:
        svc.limiter.record(ip, "login_failure")
        raise AppError(401, ErrorCode.UNAUTHORIZED, "Wrong username or password")
    return Token(access_token=issue_token(user, settings))


@router.get("/me", response_model=Me)
async def me(user: CurrentUser) -> Me:
    return user.to_me()


@router.get("/metrics", response_model=Metrics)
async def metrics(user: CurrentUser, svc: Svc) -> Metrics:
    # Aggregates span all clients, so only the demo admin may see them
    if not user.is_demo_admin:
        raise AppError(403, ErrorCode.FORBIDDEN, "Metrics are available to the demo admin only")
    store = svc.store
    traces = [t for t in store.traces.values() if t.insight_id]
    durations = store.job_durations_ms
    return Metrics(
        insights_total=len(store.insights),
        feedback_up=sum(f.rating == "up" for f in store.feedback),
        feedback_down=sum(f.rating == "down" for f in store.feedback),
        self_corrections=sum(t.retries > 0 for t in traces),
        avg_tokens_per_insight=sum(t.total_tokens for t in traces) / len(traces)
        if traces
        else None,
        avg_latency_ms=sum(durations) / len(durations) if durations else None,
    )


@router.get("/budget", response_model=Budget)
async def budget(user: CurrentUser, svc: Svc, settings: Cfg) -> Budget:
    # Real counter comes from the agent's token log (I1, I3)
    traces = svc.store.traces.values()
    used = sum(t.total_tokens for t in traces)
    limit = settings.daily_token_limit
    return Budget(
        tokens_used_today=used,
        tokens_limit_today=limit,
        cost_rub_today=round(sum(t.total_cost_rub for t in traces), 2),
        exhausted=bool(limit and used >= limit),
    )
