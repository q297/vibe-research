from fastapi import APIRouter

from app.api.deps import Cfg, Svc
from app.auth import CurrentUser, ensure_client_access
from app.context import current_trace_id, new_trace_id
from app.contracts.events import Event, NewsIngestRequest, NewsIngestResponse
from app.errors import not_found

router = APIRouter(tags=["news"])


@router.get("/events/{event_id}", response_model=Event)
async def get_event(event_id: str, user: CurrentUser, svc: Svc) -> Event:
    event = await svc.news.get_event(event_id)
    if event is None:
        raise not_found("Event")
    return event


@router.post("/news/ingest", response_model=NewsIngestResponse)
async def ingest_news(body: NewsIngestRequest, user: CurrentUser, svc: Svc, settings: Cfg):
    svc.limiter.check(user.user_id, "ingest", settings.rate_limit_ingest_per_hour)
    if body.client_id:
        ensure_client_access(user, body.client_id)
    trace_id = current_trace_id() or new_trace_id()
    event = await svc.news.ingest_text(body, trace_id=trace_id)

    job_id = None
    if body.client_id:
        profile = await svc.profiles.get_profile(body.client_id)
        if profile is None:
            raise not_found("Client")
        job = svc.jobs.active(profile.client_id, event.event_id, user.role)
        if job is None:
            svc.limiter.check(user.user_id, "run", settings.rate_limit_runs_per_hour)
            job = svc.jobs.start(
                profile=profile, event=event, role=user.role, trace_id=new_trace_id()
            )
        job_id = job.job_id
    return NewsIngestResponse(event=event, job_id=job_id)
