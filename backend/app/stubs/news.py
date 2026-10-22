import hashlib
import re
from datetime import UTC, datetime

from app.contracts.events import (
    ArticleRef,
    ClassificationStatus,
    Event,
    EventOrigin,
    NewsIngestRequest,
)
from app.contracts.insights import BankPosition
from app.contracts.taxonomy import SensitivityTag
from app.stubs import load_fixture

# Naive keyword classifier, stands in for the Gemma classifier of role 2
_KEYWORDS: dict[SensitivityTag, tuple[str, ...]] = {
    SensitivityTag.KEY_RATE: ("ставк", "цб", "банк росси"),
    SensitivityTag.FX_RATE: ("курс", "рубл", "юан", "доллар", "евро"),
    SensitivityTag.INFLATION: ("инфляц", "цен"),
    SensitivityTag.CONSUMER_DEMAND: ("потреб", "розниц", "спрос"),
    SensitivityTag.COMMODITIES_METALS: ("стал", "металл", "прокат"),
    SensitivityTag.COMMODITIES_AGRI: ("зерн", "пшениц", "урожа"),
    SensitivityTag.COMMODITIES_ENERGY: ("нефт", "газ", "уголь"),
    SensitivityTag.EXPORT_IMPORT: ("экспорт", "импорт", "пошлин"),
    SensitivityTag.SANCTIONS: ("санкц",),
    SensitivityTag.REGULATION: ("закон", "маркиров", "требован"),
    SensitivityTag.TAXES: ("налог", "ндс"),
    SensitivityTag.LOGISTICS: ("логист", "порт", "перевоз"),
}


class StubNews:
    def __init__(self) -> None:
        self._events = {e["event_id"]: Event.model_validate(e) for e in load_fixture("events.json")}
        self._positions = [
            BankPosition.model_validate(p) for p in load_fixture("bank_positions.json")
        ]

    async def list_events(self, *, since=None, tags=None) -> list[Event]:
        events = [e for e in self._events.values() if e.merged_into is None]
        if since:
            events = [e for e in events if e.ingested_at >= since]
        if tags:
            events = [e for e in events if set(e.tags) & set(tags)]
        return sorted(events, key=lambda e: e.ingested_at, reverse=True)

    async def get_event(self, event_id: str) -> Event | None:
        return self._events.get(event_id)

    async def ingest_text(self, request: NewsIngestRequest, *, trace_id: str) -> Event:
        digest = hashlib.sha256(request.text.strip().encode()).hexdigest()[:16]
        event_id = f"ev-user-{digest}"
        if event_id in self._events:
            return self._events[event_id]

        lowered = request.text.lower()
        # Match word starts only, so "порт" does not fire inside "импорт"
        tags = [
            tag
            for tag, words in _KEYWORDS.items()
            if any(re.search(rf"\b{re.escape(w)}", lowered) for w in words)
        ]
        now = datetime.now(UTC)
        title = request.title or request.text.strip().split("\n")[0][:120]
        event = Event(
            event_id=event_id,
            title=title,
            summary=None,
            tags=tags or [SensitivityTag.OTHER],
            okved_sections=["*"],
            importance=0.5,
            published_at=now,
            ingested_at=now,
            updated_at=now,
            classification_status=ClassificationStatus.CLASSIFIED,
            origin=EventOrigin.USER_INPUT,
            articles=[
                ArticleRef(
                    article_id=f"a-user-{digest}",
                    title=title,
                    source_name="Введено пользователем",
                    url=request.url,
                    published_at=now,
                    snippet=request.text[:300],
                )
            ],
        )
        self._events[event_id] = event
        return event

    async def bank_positions(self, topics: list[str]) -> list[BankPosition]:
        return [p for p in self._positions if p.topic in topics]
