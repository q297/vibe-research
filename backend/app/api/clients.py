from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import Svc
from app.auth import CurrentUser, ensure_client_access
from app.contracts.clients import ClientProfile, ClientSummary, FeedPage
from app.contracts.insights import InsightStatus, UserRole
from app.contracts.taxonomy import SensitivityTag
from app.errors import not_found

router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("", response_model=list[ClientSummary])
async def list_clients(user: CurrentUser, svc: Svc) -> list[ClientSummary]:
    return [c for c in await svc.profiles.list_clients() if c.client_id in user.client_ids]


@router.get("/{client_id}/profile", response_model=ClientProfile)
async def get_profile(client_id: str, user: CurrentUser, svc: Svc) -> ClientProfile:
    ensure_client_access(user, client_id)
    profile = await svc.profiles.get_profile(client_id)
    if profile is None:
        raise not_found("Client")
    return profile


@router.get("/{client_id}/feed", response_model=FeedPage)
async def get_feed(
    client_id: str,
    user: CurrentUser,
    svc: Svc,
    tags: Annotated[list[SensitivityTag] | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    cursor: Annotated[str | None, Query(description="Opaque, pass next_cursor back")] = None,
    role: Annotated[UserRole | None, Query(description="Defaults to the user role")] = None,
) -> FeedPage:
    ensure_client_access(user, client_id)
    profile = await svc.profiles.get_profile(client_id)
    if profile is None:
        raise not_found("Client")

    ranked = await svc.profiles.rank(profile, await svc.news.list_events(tags=tags))
    for item in ranked:
        cached = svc.store.find_insight(client_id, item.event.event_id, role or user.role)
        if cached:
            fresh = cached.event_version >= item.event.version
            item.insight_status = InsightStatus.READY if fresh else InsightStatus.STALE

    offset = int(cursor) if cursor and cursor.isdigit() else 0
    page = ranked[offset : offset + limit]
    next_cursor = str(offset + limit) if offset + limit < len(ranked) else None
    return FeedPage(items=page, next_cursor=next_cursor)
