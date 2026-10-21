"""In-memory storage for insights, traces, jobs, chats and feedback

Will move to Postgres once the schema settles; the interface stays the same
"""

from app.contracts.insights import AgentTrace, ChatMessage, Insight, Job, UserRole
from app.contracts.platform import Feedback

InsightKey = tuple[str, str, int, UserRole]


class Store:
    def __init__(self) -> None:
        self.insights: dict[str, Insight] = {}
        self.insight_by_key: dict[InsightKey, str] = {}
        self.traces: dict[str, AgentTrace] = {}
        self.jobs: dict[str, Job] = {}
        self.chats: dict[str, list[ChatMessage]] = {}
        self.feedback: list[Feedback] = []
        self.job_durations_ms: list[int] = []

    def save_insight(self, insight: Insight) -> None:
        self.insights[insight.insight_id] = insight
        key = (insight.client_id, insight.event_id, insight.event_version, insight.role)
        self.insight_by_key[key] = insight.insight_id

    def find_insight(self, client_id: str, event_id: str, role: UserRole) -> Insight | None:
        """Latest insight for the pair regardless of event version, caller checks staleness"""
        matches = [
            self.insights[iid]
            for (cid, eid, _, r), iid in self.insight_by_key.items()
            if cid == client_id and eid == event_id and r == role
        ]
        return max(matches, key=lambda i: i.event_version, default=None)
