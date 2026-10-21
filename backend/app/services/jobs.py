"""Background insight generation with a live step stream (avoids the 30 s timeout of E4)"""

import asyncio
import logging
import time
import uuid

from app.contracts.clients import ClientProfile
from app.contracts.events import Event
from app.contracts.insights import (
    AgentTrace,
    Insight,
    Job,
    JobStatus,
    StepKind,
    TraceStep,
    UserRole,
)
from app.services.ports import AgentPort
from app.services.store import Store

log = logging.getLogger("app.jobs")


class JobManager:
    def __init__(self, agent: AgentPort, store: Store) -> None:
        self._agent = agent
        self._store = store
        self._conditions: dict[str, asyncio.Condition] = {}
        self._tasks: set[asyncio.Task] = set()

    def start(self, *, profile: ClientProfile, event: Event, role: UserRole, trace_id: str) -> Job:
        job = Job(
            job_id=f"job-{uuid.uuid4().hex[:12]}",
            status=JobStatus.QUEUED,
            client_id=profile.client_id,
            event_id=event.event_id,
            role=role,
            trace_id=trace_id,
        )
        self._store.jobs[job.job_id] = job
        self._store.traces[trace_id] = AgentTrace(trace_id=trace_id)
        self._conditions[job.job_id] = asyncio.Condition()
        task = asyncio.create_task(self._run(job, profile, event))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return job

    def completed(self, insight: Insight) -> Job:
        """Job for a cache hit, so the client always follows the same flow"""
        job = Job(
            job_id=f"job-{uuid.uuid4().hex[:12]}",
            status=JobStatus.DONE,
            client_id=insight.client_id,
            event_id=insight.event_id,
            role=insight.role,
            trace_id=insight.trace_id,
            insight_id=insight.insight_id,
        )
        self._store.jobs[job.job_id] = job
        self._store.traces.setdefault(insight.trace_id, AgentTrace(trace_id=insight.trace_id))
        self._conditions[job.job_id] = asyncio.Condition()
        return job

    async def _notify(self, job_id: str) -> None:
        condition = self._conditions[job_id]
        async with condition:
            condition.notify_all()

    async def _run(self, job: Job, profile: ClientProfile, event: Event) -> None:
        trace = self._store.traces[job.trace_id]
        started = time.perf_counter()
        job.status = JobStatus.RUNNING
        await self._notify(job.job_id)
        try:
            async for item in self._agent.run(
                profile=profile, event=event, role=job.role, trace_id=job.trace_id
            ):
                if isinstance(item, TraceStep):
                    trace.steps.append(item)
                    trace.total_tokens += (item.tokens_in or 0) + (item.tokens_out or 0)
                    if item.kind == StepKind.RETRY:
                        trace.retries += 1
                elif isinstance(item, Insight):
                    self._store.save_insight(item)
                    trace.insight_id = item.insight_id
                    job.insight_id = item.insight_id
                await self._notify(job.job_id)
            job.status = JobStatus.DONE if job.insight_id else JobStatus.FAILED
            if not job.insight_id:
                job.error = "Agent finished without an insight"
        except Exception as exc:
            log.exception("job %s failed", job.job_id)
            job.status = JobStatus.FAILED
            job.error = type(exc).__name__
        finally:
            self._store.job_durations_ms.append(round((time.perf_counter() - started) * 1000))
            await self._notify(job.job_id)

    async def wait_for_change(self, job_id: str, seen_steps: int, timeout: float = 15) -> None:
        condition = self._conditions[job_id]
        job = self._store.jobs[job_id]
        trace = self._store.traces[job.trace_id]
        async with condition:
            try:
                await asyncio.wait_for(
                    condition.wait_for(
                        lambda: (
                            len(trace.steps) > seen_steps
                            or job.status in (JobStatus.DONE, JobStatus.FAILED)
                        )
                    ),
                    timeout,
                )
            except TimeoutError:
                pass
