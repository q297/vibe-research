import asyncio
import json

from app.contracts.insights import Insight, TraceStep


async def test_health_is_public(client):
    resp = await client.get("/v1/health")
    assert resp.status_code == 200
    assert resp.json()["mock_mode"] is True
    assert resp.headers["X-Trace-Id"].startswith("tr-")


async def test_errors_use_single_shape(client):
    resp = await client.get("/v1/me")
    assert resp.status_code == 401
    body = resp.json()
    assert body["code"] == "unauthorized"
    assert body["trace_id"].startswith("tr-")


async def test_wrong_password(client):
    resp = await client.post("/v1/auth/login", json={"username": "demo", "password": "nope"})
    assert resp.status_code == 401


async def test_user_sees_only_own_clients(client, login):
    headers = await login("cfo.a")
    clients = (await client.get("/v1/clients", headers=headers)).json()
    assert [c["client_id"] for c in clients] == ["c-001"]
    resp = await client.get("/v1/clients/c-002/feed", headers=headers)
    assert resp.status_code == 403
    assert resp.json()["code"] == "forbidden"


async def test_feed_differs_between_clients(client, login):
    headers = await login("demo")
    feeds = {}
    for cid in ("c-001", "c-002", "c-003"):
        resp = await client.get(f"/v1/clients/{cid}/feed", headers=headers)
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert items and all(i["why_relevant"] for i in items)
        feeds[cid] = [i["event"]["event_id"] for i in items]
    assert feeds["c-001"][0] != feeds["c-002"][0]
    assert "ev-006" in feeds["c-002"] and "ev-006" not in feeds["c-001"]
    assert "ev-007" in feeds["c-003"]


async def test_feed_pagination(client, login):
    headers = await login("demo")
    first = (await client.get("/v1/clients/c-001/feed?limit=2", headers=headers)).json()
    assert len(first["items"]) == 2 and first["next_cursor"]
    second = (
        await client.get(
            f"/v1/clients/c-001/feed?limit=2&cursor={first['next_cursor']}", headers=headers
        )
    ).json()
    ids = {i["event"]["event_id"] for i in first["items"]}
    assert ids.isdisjoint(i["event"]["event_id"] for i in second["items"])


async def _run_and_stream(client, headers, client_id, event_id, **body):
    resp = await client.post(
        f"/v1/clients/{client_id}/insights/{event_id}/run", json=body, headers=headers
    )
    assert resp.status_code == 202, resp.text
    job = resp.json()
    steps, final = [], None
    async with client.stream("GET", f"/v1/jobs/{job['job_id']}/stream", headers=headers) as stream:
        event = None
        async for line in stream.aiter_lines():
            if line.startswith("event: "):
                event = line.removeprefix("event: ")
            elif line.startswith("data: "):
                data = json.loads(line.removeprefix("data: "))
                if event == "step":
                    steps.append(TraceStep.model_validate(data))
                elif event == "job":
                    final = data
    return job, steps, final


async def test_insight_job_streams_steps_and_caches(client, login):
    headers = await login("demo")
    _, steps, final = await _run_and_stream(client, headers, "c-001", "ev-001")
    assert final["status"] == "done"
    kinds = [s.kind for s in steps]
    assert kinds[0] == "plan" and kinds[-1] == "final" and "critic" in kinds

    insight = Insight.model_validate(
        (await client.get(f"/v1/insights/{final['insight_id']}", headers=headers)).json()
    )
    assert insight.bank_positions and insight.why_it_matters
    assert {c.provenance for c in insight.why_it_matters} == {"ai_inference"}

    trace = (await client.get(f"/v1/insights/{insight.insight_id}/trace", headers=headers)).json()
    assert len(trace["steps"]) == len(steps)

    feed = (await client.get("/v1/clients/c-001/feed", headers=headers)).json()
    status = {i["event"]["event_id"]: i["insight_status"] for i in feed["items"]}
    assert status["ev-001"] == "ready"

    cached, _, _ = await _run_and_stream(client, headers, "c-001", "ev-001")
    assert cached["status"] == "done" and cached["insight_id"] == insight.insight_id


async def test_critic_retry_when_no_bank_position(client, login):
    headers = await login("demo")
    _, steps, final = await _run_and_stream(client, headers, "c-003", "ev-007")
    assert final["status"] == "done"
    assert any(s.kind == "retry" for s in steps)


async def test_other_user_cannot_read_insight(client, login):
    admin = await login("demo")
    _, _, final = await _run_and_stream(client, admin, "c-001", "ev-001")
    other = await login("ceo.b")
    resp = await client.get(f"/v1/insights/{final['insight_id']}", headers=other)
    assert resp.status_code == 403


async def test_chat_and_feedback(client, login):
    headers = await login("demo")
    _, _, final = await _run_and_stream(client, headers, "c-001", "ev-001")
    iid = final["insight_id"]
    resp = await client.post(
        f"/v1/insights/{iid}/chat", json={"message": "А если ставка вырастет?"}, headers=headers
    )
    assert resp.status_code == 200
    assert [m["role"] for m in resp.json()["messages"]] == ["user", "assistant"]
    resp = await client.post(
        "/v1/feedback", json={"insight_id": iid, "rating": "up"}, headers=headers
    )
    assert resp.status_code == 201
    metrics = (await client.get("/v1/metrics", headers=headers)).json()
    assert metrics["feedback_up"] == 1 and metrics["insights_total"] == 1


async def test_login_failures_are_limited_per_ip(client, monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_LOGIN_FAILURES_PER_HOUR", "2")
    from app.config import get_settings

    get_settings.cache_clear()
    bad = {"username": "demo", "password": "wrong"}
    for _ in range(2):
        assert (await client.post("/v1/auth/login", json=bad)).status_code == 401
    resp = await client.post("/v1/auth/login", json=bad)
    assert resp.status_code == 429 and resp.json()["code"] == "rate_limited"


async def test_successful_logins_are_not_limited(client, login, monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_LOGIN_FAILURES_PER_HOUR", "1")
    from app.config import get_settings

    get_settings.cache_clear()
    for _ in range(3):
        await login("demo")


async def test_metrics_only_for_demo_admin(client, login):
    resp = await client.get("/v1/metrics", headers=await login("cfo.a"))
    assert resp.status_code == 403
    resp = await client.get("/v1/metrics", headers=await login("demo"))
    assert resp.status_code == 200


async def test_ingest_user_news_is_idempotent_and_starts_job(client, login):
    headers = await login("demo")
    text = "Правительство обсуждает новые экспортные пошлины на пшеницу и другие зерновые культуры"
    first = await client.post(
        "/v1/news/ingest", json={"text": text, "client_id": "c-003"}, headers=headers
    )
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["event"]["origin"] == "user_input"
    assert "commodities_agri" in body["event"]["tags"]
    assert body["job_id"]
    second = await client.post("/v1/news/ingest", json={"text": text}, headers=headers)
    assert second.json()["event"]["event_id"] == body["event"]["event_id"]


async def test_ingest_validates_length(client, login):
    headers = await login("demo")
    resp = await client.post("/v1/news/ingest", json={"text": "short"}, headers=headers)
    assert resp.status_code == 422
    assert resp.json()["code"] == "bad_request"


async def test_rate_limit(client, login, monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_CHAT_PER_HOUR", "1")
    from app.config import get_settings

    get_settings.cache_clear()
    headers = await login("demo")
    _, _, final = await _run_and_stream(client, headers, "c-001", "ev-001")
    url = f"/v1/insights/{final['insight_id']}/chat"
    assert (await client.post(url, json={"message": "1"}, headers=headers)).status_code == 200
    resp = await client.post(url, json={"message": "2"}, headers=headers)
    assert resp.status_code == 429 and resp.json()["code"] == "rate_limited"


async def _wait_warmup(client, headers):
    for _ in range(200):
        status = (await client.get("/v1/admin/warm-cache", headers=headers)).json()
        if not status["running"]:
            return status
        await asyncio.sleep(0.01)
    raise AssertionError("warm-up did not finish")


async def test_warm_cache_computes_then_skips(client, login):
    headers = await login("demo")
    body = {"client_ids": ["c-001", "c-002"], "top": 2, "roles": ["cfo", "ceo"]}
    resp = await client.post("/v1/admin/warm-cache", json=body, headers=headers)
    assert resp.status_code == 202
    first = await _wait_warmup(client, headers)
    assert first["total"] == 8 and first["computed"] == 8 and first["failed"] == 0

    feed = (await client.get("/v1/clients/c-001/feed?limit=2&role=ceo", headers=headers)).json()
    assert {i["insight_status"] for i in feed["items"]} == {"ready"}

    await client.post("/v1/admin/warm-cache", json=body, headers=headers)
    second = await _wait_warmup(client, headers)
    assert second["skipped"] == 8 and second["computed"] == 0


async def test_warm_cache_is_admin_only(client, login):
    resp = await client.post("/v1/admin/warm-cache", json={}, headers=await login("cfo.a"))
    assert resp.status_code == 403
