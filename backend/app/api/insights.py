from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Query, status
from fastapi.responses import StreamingResponse

from app.api.deps import Cfg, Svc
from app.auth import CurrentUser, UserRecord, ensure_client_access
from app.context import new_trace_id
from app.contracts.insights import (
    AgentTrace,
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ChatRole,
    Insight,
    InsightStatus,
    Job,
    JobStatus,
    RunInsightRequest,
    UserRole,
)
from app.errors import not_found
from app.services.registry import Services

router = APIRouter(tags=["insights"])


def _owned_insight(svc: Services, user: UserRecord, insight_id: str) -> Insight:
    insight = svc.store.insights.get(insight_id)
    if insight is None:
        raise not_found("Insight")
    ensure_client_access(user, insight.client_id)
    return insight


def _owned_job(svc: Services, user: UserRecord, job_id: str) -> Job:
    job = svc.store.jobs.get(job_id)
    if job is None:
        raise not_found("Job")
    ensure_client_access(user, job.client_id)
    return job


@router.get("/clients/{client_id}/insights/{event_id}", response_model=Insight)
async def get_insight(
    client_id: str,
    event_id: str,
    user: CurrentUser,
    svc: Svc,
    role: Annotated[UserRole | None, Query()] = None,
) -> Insight:
    ensure_client_access(user, client_id)
    insight = svc.store.find_insight(client_id, event_id, role or user.role)
    if insight is None:
        raise not_found("Insight")
    event = await svc.news.get_event(event_id)
    if event and event.version > insight.event_version:
        return insight.model_copy(update={"status": InsightStatus.STALE})
    return insight


@router.post(
    "/clients/{client_id}/insights/{event_id}/run",
    response_model=Job,
    status_code=status.HTTP_202_ACCEPTED,
)
async def run_insight(
    client_id: str,
    event_id: str,
    body: RunInsightRequest,
    user: CurrentUser,
    svc: Svc,
    settings: Cfg,
) -> Job:
    ensure_client_access(user, client_id)
    role = body.role or user.role
    profile = await svc.profiles.get_profile(client_id)
    event = await svc.news.get_event(event_id)
    if profile is None:
        raise not_found("Client")
    if event is None:
        raise not_found("Event")

    cached = svc.store.find_insight(client_id, event_id, role)
    if cached and not body.force and cached.event_version >= event.version:
        return svc.jobs.completed(cached)

    running = svc.jobs.active(client_id, event_id, role)
    if running:
        return running
    svc.limiter.check(user.user_id, "run", settings.rate_limit_runs_per_hour)
    return svc.jobs.start(profile=profile, event=event, role=role, trace_id=new_trace_id())


@router.get("/jobs/{job_id}", response_model=Job)
async def get_job(job_id: str, user: CurrentUser, svc: Svc) -> Job:
    return _owned_job(svc, user, job_id)


@router.get(
    "/jobs/{job_id}/stream",
    response_class=StreamingResponse,
    responses={200: {"content": {"text/event-stream": {}}, "description": "SSE: step, job events"}},
)
async def stream_job(job_id: str, user: CurrentUser, svc: Svc) -> StreamingResponse:
    """Server-sent events: 'step' carries a TraceStep, 'job' carries the Job, the last 'job' is final"""
    job = _owned_job(svc, user, job_id)

    async def events() -> AsyncIterator[str]:
        sent = 0
        while True:
            trace = svc.store.traces[job.trace_id]
            for step in trace.steps[sent:]:
                yield f"event: step\ndata: {step.model_dump_json()}\n\n"
            sent = len(trace.steps)
            if job.status in (JobStatus.DONE, JobStatus.FAILED):
                yield f"event: job\ndata: {job.model_dump_json()}\n\n"
                return
            yield ": keep-alive\n\n"
            await svc.jobs.wait_for_change(job.job_id, sent)

    headers = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    return StreamingResponse(events(), media_type="text/event-stream", headers=headers)


@router.get("/insights/{insight_id}", response_model=Insight)
async def get_insight_by_id(insight_id: str, user: CurrentUser, svc: Svc) -> Insight:
    return _owned_insight(svc, user, insight_id)


@router.get("/insights/{insight_id}/trace", response_model=AgentTrace)
async def get_trace(insight_id: str, user: CurrentUser, svc: Svc) -> AgentTrace:
    insight = _owned_insight(svc, user, insight_id)
    trace = svc.store.traces.get(insight.trace_id)
    if trace is None:
        raise not_found("Trace")
    return trace


@router.get("/insights/{insight_id}/chat", response_model=list[ChatMessage])
async def get_chat(insight_id: str, user: CurrentUser, svc: Svc) -> list[ChatMessage]:
    _owned_insight(svc, user, insight_id)
    return svc.store.chat(user.user_id, insight_id)


@router.post("/insights/{insight_id}/chat", response_model=ChatResponse)
async def post_chat(
    insight_id: str, body: ChatRequest, user: CurrentUser, svc: Svc, settings: Cfg
) -> ChatResponse:
    insight = _owned_insight(svc, user, insight_id)
    svc.limiter.check(user.user_id, "chat", settings.rate_limit_chat_per_hour)
    history = svc.store.chat(user.user_id, insight_id)
    question = ChatMessage(role=ChatRole.USER, content=body.message, created_at=datetime.now(UTC))
    trace_id = new_trace_id()
    answer = await svc.agent.chat(
        insight=insight, history=list(history), message=body.message, trace_id=trace_id
    )
    await svc.store.add_chat(user.user_id, insight_id, [question, answer])
    return ChatResponse(messages=[question, answer], trace_id=trace_id)
