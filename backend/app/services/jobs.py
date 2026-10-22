"""Background insight generation with a live step stream (avoids the 30 s timeout of E4)"""

import asyncio
import logging
import time
import uuid

from app.contracts.clients import ClientProfile
from app.contracts.common import ErrorCode
from app.contracts.events import Event
from app.contracts.insights import (
    AgentTrace,
    Insight,
    InsightStatus,
    Job,
    JobStatus,
    StepKind,
    TraceStep,
    UserRole,
)
from app.services.ports import AgentPort, BudgetExhausted
from app.services.store import Store

log = logging.getLogger("app.jobs")


class JobManager:
    def __init__(self, agent: AgentPort, store: Store) -> None:
        self._agent = agent
        self._store = store
        self._conditions: dict[str, asyncio.Condition] = {}
        self._tasks: set[asyncio.Task] = set()

    def active(self, client_id: str, event_id: str, role: UserRole) -> Job | None:
        """Job already computing this pair, so repeated clicks share one agent run"""
        for job in self._store.jobs.values():
            if job.status in (JobStatus.QUEUED, JobStatus.RUNNING) and (
                job.client_id,
                job.event_id,
                job.role,
            ) == (client_id, event_id, role):
                return job
        return None

    def start(self, *, profile: ClientProfile, event: Event, role: UserRole, trace_id: str) -> Job:
        running = self.active(profile.client_id, event.event_id, role)
        if running:
            return running
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
                    trace.total_cost_rub += item.cost_rub or 0
                    if item.kind == StepKind.RETRY:
                        trace.retries += 1
                elif isinstance(item, Insight) and item.status == InsightStatus.FAILED:
                    # Failed insights never reach the cache, the gaps explain why
                    job.error_code = ErrorCode.UPSTREAM_FAILED
                    job.error = "; ".join(item.data_gaps) or "Agent failed"
                elif isinstance(item, Insight):
                    await self._store.save_insight(item)
                    trace.insight_id = item.insight_id
                    job.insight_id = item.insight_id
                await self._notify(job.job_id)
            job.status = JobStatus.DONE if job.insight_id else JobStatus.FAILED
            if not job.insight_id and not job.error:
                job.error_code = ErrorCode.UPSTREAM_FAILED
                job.error = "Agent finished without an insight"
        except BudgetExhausted:
            job.status = JobStatus.FAILED
            job.error_code = ErrorCode.BUDGET_EXHAUSTED
            job.error = "Daily LLM budget is exhausted"
        except Exception as exc:
            log.exception("job %s failed", job.job_id)
            job.status = JobStatus.FAILED
            job.error_code = ErrorCode.INTERNAL
            job.error = type(exc).__name__
        finally:
            try:
                await self._store.finish_job(job, round((time.perf_counter() - started) * 1000))
            except Exception:
                # The run itself is done, losing its log row must not hang the stream
                log.exception("job %s: failed to persist run", job.job_id)
            await self._notify(job.job_id)

    async def wait_done(self, job_id: str) -> Job:
        job = self._store.jobs[job_id]
        while job.status not in (JobStatus.DONE, JobStatus.FAILED):
            await self.wait_for_change(job_id, len(self._store.traces[job.trace_id].steps))
        return job

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
