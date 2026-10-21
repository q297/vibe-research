from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.contracts.clients import ClientProfile, DebtLoad
from app.contracts.events import Event
from app.contracts.taxonomy import SensitivityTag as T
from app.profiling import ranker
from app.profiling.countries import parse_countries
from app.profiling.parsing import gradation_midpoint, parse_flag, parse_number
from app.profiling.sectors import normalize_okved, sector_name
from app.profiling.service import CsvProfiles
from app.stubs import load_fixture

DATA = Path(__file__).parents[1] / "app/profiling/synthetic_data"
NOW = datetime(2026, 10, 20, tzinfo=UTC)


@pytest.fixture(scope="module")
def profiles() -> CsvProfiles:
    return CsvProfiles(DATA, pinned=["c-001", "c-002", "c-003"])


@pytest.fixture(scope="module")
def events() -> list[Event]:
    return [Event.model_validate(e) for e in load_fixture("events.json")]


def _sens(p: ClientProfile) -> dict[T, float]:
    return {s.tag: s.weight for s in p.sensitivities}


def test_parsers_survive_noise():
    assert parse_flag("да") is True and parse_flag("0.0") is False and parse_flag("") is None
    assert parse_number("1 234,5") == 1234.5 and parse_number("abc") is None
    assert gradation_midpoint("от 100 до 250") == 175
    assert gradation_midpoint("1-3 года") == 2
    assert gradation_midpoint("до 100") == 50
    assert gradation_midpoint(None) is None
    assert normalize_okved("2410") == "24.10" and normalize_okved("nan") is None
    assert sector_name("46.71.1") == "Оптовая торговля топливом"
    assert sector_name("46.90") == "Оптовая торговля"
    assert parse_countries("Китай; ОАЭ, Неведомия") == (["CN", "AE"], ["Китай", "ОАЭ", "Неведомия"])


async def test_every_profile_validates(profiles):
    for cid in list(profiles.dataset.companies)[:150]:
        profile = await profiles.get_profile(cid)
        ClientProfile.model_validate(profile.model_dump())


async def test_list_clients_pins_demo_and_keeps_large(profiles):
    clients = await profiles.list_clients()
    assert [c.client_id for c in clients[:3]] == ["c-001", "c-002", "c-003"]
    assert all((c.revenue_bn_rub or 0) >= 15 for c in clients)


async def test_profiles_reflect_csv_features(profiles):
    steel = await profiles.get_profile("c-001")
    retail = await profiles.get_profile("c-002")
    assert steel.debt_load == DebtLoad.MEDIUM and retail.debt_load == DebtLoad.NONE
    assert steel.foreign_trade.countries == ["CN", "TR"]
    assert _sens(steel)[T.KEY_RATE] > 0.9 and _sens(steel)[T.COMMODITIES_METALS] > 0.9
    assert _sens(retail)[T.CONSUMER_DEMAND] > 0.9 and T.COMMODITIES_METALS not in _sens(retail)
    assert all(s.evidence for s in steel.sensitivities)
    rate = next(s for s in steel.sensitivities if s.tag == T.KEY_RATE)
    assert "products.credit" in rate.evidence


async def test_graph_finds_counterparties_and_affiliates(profiles):
    dev = await profiles.get_profile("c-004")
    cement = next(c for c in dev.top_counterparties if c.sector == "Производство стройматериалов")
    assert cement.role == "supplier" and cement.share > 0.5
    assert 0 < dev.counterparty_concentration <= 1
    sister = next(a for a in dev.affiliates if a.client_id == cement.counterparty_id)
    assert sister.link == "group" and sister.shared_persons == 2
    assert "f-9999" not in profiles.dataset.companies_by_person


async def test_missing_data_is_unknown_not_no(profiles):
    trader = await profiles.get_profile("c-005")
    assert trader.debt_load is None  # potential client, product flags empty
    assert trader.foreign_trade.has_fea is True  # flag empty, but a country is given
    assert "products" in trader.data_quality.missing_fields
    assert trader.data_quality.completeness < 1


async def test_feed_differs_between_clients(profiles, events):
    feeds = {}
    for cid in ("c-001", "c-002", "c-003"):
        items = ranker.rank(await profiles.get_profile(cid), events, now=NOW)
        assert items and all(i.why_relevant for i in items)
        feeds[cid] = [i.event.event_id for i in items]
    assert feeds["c-001"][0] == "ev-003"  # steel prices and China for the steel exporter
    assert feeds["c-003"][0] == "ev-007"  # wheat export duty for the agro exporter
    assert feeds["c-001"][0] != feeds["c-002"][0]
    assert "ev-006" in feeds["c-002"] and "ev-006" not in feeds["c-001"]
    assert "ev-008" not in feeds["c-001"]  # unclassified events never match


async def test_reasons_explain_the_score(profiles, events):
    profile = await profiles.get_profile("c-001")
    item = next(i for i in ranker.rank(profile, events, now=NOW) if i.event.event_id == "ev-003")
    labels = " | ".join(r.label for r in item.why_relevant)
    assert "Китай" in labels and "покупатель" in labels  # ВЭД and the payment graph
    weights = [r.weight for r in item.why_relevant]
    assert weights == sorted(weights, reverse=True) and all(w > 0 for w in weights)
    assert len({r.label for r in item.why_relevant}) == len(item.why_relevant)


async def test_rank_is_deterministic(profiles, events):
    profile = await profiles.get_profile("c-002")
    first = ranker.rank(profile, events, now=NOW)
    assert first == ranker.rank(profile, list(reversed(events)), now=NOW)


async def test_api_serves_csv_profiles(monkeypatch, client, login):
    from app.config import get_settings
    from app.services.registry import get_services

    monkeypatch.setenv("PROFILES_DATA_DIR", str(DATA))
    get_settings.cache_clear()
    get_services.cache_clear()
    headers = await login("demo")
    clients = (await client.get("/v1/clients", headers=headers)).json()
    assert {c["client_id"] for c in clients} == {"c-001", "c-002", "c-003"}
    profile = (await client.get("/v1/clients/c-001/profile", headers=headers)).json()
    assert profile["sector"] == "Металлургия" and profile["top_counterparties"]
    feed = (await client.get("/v1/clients/c-003/feed", headers=headers)).json()
    assert feed["items"][0]["event"]["event_id"] == "ev-007"
