import asyncio
from datetime import UTC, datetime

import pytest

from app.contracts.insights import Insight, InsightStatus, StepKind, StepStatus, TraceStep
from app.services.jobs import JobManager
from app.services.ports import BudgetExhausted
from app.services.registry import get_services
from tests.insight_invariants import insight_violations
from tests.test_api import _run_and_stream


@pytest.mark.parametrize("client_id", ["c-001", "c-002", "c-003"])
async def test_stub_agent_keeps_insight_invariants(client_id):
    svc = get_services()
    profile = await svc.profiles.get_profile(client_id)
    for event in await svc.news.list_events():
        items = [
            i
            async for i in svc.agent.run(profile=profile, event=event, role="cfo", trace_id="tr-t")
        ]
        insight = items[-1]
        assert isinstance(insight, Insight)
        assert insight_violations(insight) == [], event.event_id


def _use_agent(agent) -> None:
    svc = get_services()
    svc.agent = agent
    svc.jobs = JobManager(agent, svc.store)


class FailingAgent:
    async def run(self, *, profile, event, role, trace_id):
        now = datetime.now(UTC)
        yield TraceStep(index=1, kind=StepKind.PLAN, title="plan", started_at=now)
        yield TraceStep(
            index=2, kind=StepKind.DRAFT, title="draft", status=StepStatus.ERROR, started_at=now
        )
        yield Insight(
            insight_id="ins-failed",
            client_id=profile.client_id,
            event_id=event.event_id,
            event_version=event.version,
            role=role,
            status=InsightStatus.FAILED,
            headline="",
            data_gaps=["Модель вернула невалидный JSON"],
            trace_id=trace_id,
            created_at=now,
        )

    async def chat(self, **_):
        raise BudgetExhausted


class BrokeAgent:
    async def run(self, **_):
        raise BudgetExhausted
        yield  # makes this an async generator

    async def chat(self, **_):
        raise BudgetExhausted


class SlowAgent:
    def __init__(self) -> None:
        self.release = asyncio.Event()
        self.runs = 0

    async def run(self, *, profile, event, role, trace_id):
        self.runs += 1
        await self.release.wait()
        async for item in FailingAgent().run(
            profile=profile, event=event, role=role, trace_id=trace_id
        ):
            yield item


async def test_failed_insight_is_not_cached(client, login):
    _use_agent(FailingAgent())
    headers = await login("demo")
    _, steps, final = await _run_and_stream(client, headers, "c-001", "ev-001")
    assert final["status"] == "failed"
    assert final["error_code"] == "upstream_failed"
    assert "невалидный JSON" in final["error"]
    assert [s.status for s in steps] == ["ok", "error"]
    assert get_services().store.insights == {}
    resp = await client.get("/v1/clients/c-001/insights/ev-001", headers=headers)
    assert resp.status_code == 404


async def test_budget_exhausted_fails_job_and_chat(client, login):
    headers = await login("demo")
    _, _, ready = await _run_and_stream(client, headers, "c-001", "ev-001")

    _use_agent(BrokeAgent())
    _, _, final = await _run_and_stream(client, headers, "c-001", "ev-001", force=True)
    assert final["status"] == "failed" and final["error_code"] == "budget_exhausted"

    resp = await client.post(
        f"/v1/insights/{ready['insight_id']}/chat", json={"message": "?"}, headers=headers
    )
    assert resp.status_code == 503 and resp.json()["code"] == "budget_exhausted"

    # The previous insight is still served from the cache
    cached = await client.get("/v1/clients/c-001/insights/ev-001", headers=headers)
    assert cached.status_code == 200


async def test_repeated_run_reuses_active_job(client, login):
    agent = SlowAgent()
    _use_agent(agent)
    headers = await login("demo")
    url = "/v1/clients/c-001/insights/ev-001/run"
    first = (await client.post(url, json={}, headers=headers)).json()
    second = (await client.post(url, json={}, headers=headers)).json()
    assert first["job_id"] == second["job_id"]
    agent.release.set()
    await asyncio.sleep(0)
    assert agent.runs == 1


async def test_user_news_facts_cite_user_input(client, login):
    headers = await login("demo")
    text = "Банк России сохранил ключевую ставку, рынок ждал этого решения уже несколько недель"
    event = (await client.post("/v1/news/ingest", json={"text": text}, headers=headers)).json()
    event_id = event["event"]["event_id"]
    _, _, final = await _run_and_stream(client, headers, "c-001", event_id)
    insight = Insight.model_validate(
        (await client.get(f"/v1/insights/{final['insight_id']}", headers=headers)).json()
    )
    assert {c.kind for claim in insight.what_happened for c in claim.citations} == {"user_input"}
