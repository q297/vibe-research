"""Precomputes insights for the top of each demo client feed, one agent run at a time"""

import asyncio
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.context import new_trace_id
from app.contracts.common import ErrorCode
from app.contracts.insights import JobStatus, UserRole
from app.contracts.platform import WarmupRequest, WarmupStatus

if TYPE_CHECKING:
    from app.services.registry import Services

log = logging.getLogger("app.warmup")


class Warmup:
    def __init__(self) -> None:
        self.status = WarmupStatus()
        self._task: asyncio.Task | None = None

    def start(
        self, services: "Services", request: WarmupRequest, client_ids: list[str], role: UserRole
    ) -> WarmupStatus:
        self.status = WarmupStatus(running=True, started_at=datetime.now(UTC))
        roles = request.roles or [role]
        self._task = asyncio.create_task(self._run(services, request, client_ids, roles))
        return self.status

    async def _run(
        self,
        svc: "Services",
        request: WarmupRequest,
        client_ids: list[str],
        roles: list[UserRole],
    ) -> None:
        status = self.status
        try:
            events = await svc.news.list_events()
            pairs = []
            for client_id in client_ids:
                profile = await svc.profiles.get_profile(client_id)
                if profile is None:
                    continue
                ranked = await svc.profiles.rank(profile, events)
                pairs += [(profile, item.event.event_id) for item in ranked[: request.top]]
            status.total = len(pairs) * len(roles)

            # Sequential on purpose: the LLM budget is shared, a burst would drain it
            for profile, event_id in pairs:
                event = await svc.news.get_event(event_id)
                if event is None:
                    status.failed += len(roles)
                    continue
                for role in roles:
                    status.current = f"{profile.client_id}:{event_id}:{role.value}"
                    cached = svc.store.find_insight(profile.client_id, event_id, role)
                    if cached and not request.force and cached.event_version >= event.version:
                        status.skipped += 1
                        continue
                    job = svc.jobs.start(
                        profile=profile, event=event, role=role, trace_id=new_trace_id()
                    )
                    job = await svc.jobs.wait_done(job.job_id)
                    if job.status == JobStatus.DONE:
                        status.computed += 1
                        continue
                    status.failed += 1
                    if job.error_code == ErrorCode.BUDGET_EXHAUSTED:
                        status.error = "Daily LLM budget is exhausted, warm-up stopped"
                        return
        except Exception as exc:
            log.exception("warm-up failed")
            status.error = type(exc).__name__
        finally:
            status.running = False
            status.current = None
            status.finished_at = datetime.now(UTC)
