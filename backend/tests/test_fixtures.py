"""Fixtures are part of the contract: they must always validate against the schemas"""

from app.contracts.clients import ClientProfile
from app.contracts.events import Event
from app.contracts.insights import BankPosition
from app.stubs import load_fixture


def test_clients_fixture_valid():
    for item in load_fixture("clients.json"):
        ClientProfile.model_validate(item)


def test_events_fixture_valid():
    events = [Event.model_validate(e) for e in load_fixture("events.json")]
    assert len({e.event_id for e in events}) == len(events)
    assert all(e.origin == "synthetic" for e in events)


def test_bank_positions_fixture_valid():
    for item in load_fixture("bank_positions.json"):
        BankPosition.model_validate(item)
