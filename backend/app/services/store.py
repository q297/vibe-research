"""Working set of insights, traces, jobs, chats and feedback

Everything durable is written through to the repository and loaded back on startup,
jobs and in-flight traces live only in memory. Fine for thousands of insights; past
that, reads should go to the repository instead of the in-memory dicts
"""

from app.contracts.insights import AgentTrace, ChatMessage, Insight, Job, UserRole
from app.contracts.platform import Feedback
from app.services.repository import MemoryRepository, Repository, chat_key

InsightKey = tuple[str, str, int, UserRole]


class Store:
    def __init__(self, repo: Repository | None = None) -> None:
        self.repo: Repository = repo or MemoryRepository()
        self.insights: dict[str, Insight] = {}
        self.insight_by_key: dict[InsightKey, str] = {}
        self.traces: dict[str, AgentTrace] = {}
        self.jobs: dict[str, Job] = {}
        self.chats: dict[str, list[ChatMessage]] = {}
        self.feedback: list[Feedback] = []
        self.job_durations_ms: list[int] = []

    async def load(self) -> None:
        snapshot = await self.repo.load()
        for insight in snapshot.insights:
            self._index_insight(insight)
        self.traces.update({t.trace_id: t for t in snapshot.traces})
        self.feedback = snapshot.feedback
        self.chats = snapshot.chats
        self.job_durations_ms = snapshot.job_durations_ms

    def _index_insight(self, insight: Insight) -> None:
        self.insights[insight.insight_id] = insight
        key = (insight.client_id, insight.event_id, insight.event_version, insight.role)
        self.insight_by_key[key] = insight.insight_id

    async def save_insight(self, insight: Insight) -> None:
        await self.repo.save_insight(insight)
        self._index_insight(insight)

    async def finish_job(self, job: Job, duration_ms: int) -> None:
        self.job_durations_ms.append(duration_ms)
        await self.repo.save_job_run(job, self.traces[job.trace_id], duration_ms)

    async def add_feedback(self, item: Feedback) -> None:
        await self.repo.save_feedback(item)
        self.feedback.append(item)

    def chat(self, user_id: str, insight_id: str) -> list[ChatMessage]:
        return self.chats.get(chat_key(user_id, insight_id), [])

    async def add_chat(self, user_id: str, insight_id: str, messages: list[ChatMessage]) -> None:
        await self.repo.save_chat(user_id, insight_id, messages)
        self.chats.setdefault(chat_key(user_id, insight_id), []).extend(messages)

    def find_insight(self, client_id: str, event_id: str, role: UserRole) -> Insight | None:
        """Latest insight for the pair regardless of event version, caller checks staleness"""
        matches = [
            self.insights[iid]
            for (cid, eid, _, r), iid in self.insight_by_key.items()
            if cid == client_id and eid == event_id and r == role
        ]
        return max(matches, key=lambda i: i.event_version, default=None)
