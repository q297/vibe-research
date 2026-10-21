from datetime import UTC, datetime

from app.contracts.clients import (
    ClientProfile,
    ClientSummary,
    FeedItem,
    RelevanceReason,
)
from app.contracts.events import Event, EventListItem
from app.contracts.taxonomy import SensitivityTag
from app.stubs import load_fixture


def _okved_matches(client_okved: str | None, sections: list[str]) -> bool:
    if not client_okved:
        return False
    return any(s != "*" and client_okved.startswith(s) for s in sections)


class StubProfiles:
    """Tag-overlap ranking, stands in for rank(client, news) of role 3"""

    def __init__(self) -> None:
        self._profiles = {
            p["client_id"]: ClientProfile.model_validate(p) for p in load_fixture("clients.json")
        }

    async def list_clients(self) -> list[ClientSummary]:
        return [
            ClientSummary.model_validate(p.model_dump(include=set(ClientSummary.model_fields)))
            for p in self._profiles.values()
        ]

    async def get_profile(self, client_id: str) -> ClientProfile | None:
        return self._profiles.get(client_id)

    async def rank(self, profile: ClientProfile, events: list[Event]) -> list[FeedItem]:
        weights = {s.tag: s for s in profile.sensitivities}
        now = datetime.now(UTC)
        items: list[FeedItem] = []
        for event in events:
            reasons: list[RelevanceReason] = []
            score = 0.0
            for tag in event.tags:
                if tag in weights and tag != SensitivityTag.OTHER:
                    score += weights[tag].weight
                    reasons.append(
                        RelevanceReason(
                            feature=f"sensitivity.{tag.value}", label=weights[tag].reason, tag=tag
                        )
                    )
            if _okved_matches(profile.okved_code, event.okved_sections):
                score += 0.5
                reasons.append(
                    RelevanceReason(feature="okved", label=f"Ваша отрасль: {profile.okved_name}")
                )
            if profile.region and profile.region in event.regions:
                score += 0.3
                reasons.append(
                    RelevanceReason(feature="region", label=f"Ваш регион: {profile.region}")
                )
            if score == 0:
                continue

            age_days = (now - (event.published_at or event.ingested_at)).days
            freshness = max(0.3, 1 - age_days / 30)
            score *= (0.5 + (event.importance or 0.5)) * freshness
            list_item = EventListItem.model_validate(
                event.model_dump(exclude={"entities", "articles"})
                | {"source_count": max(1, len(event.articles))}
            )
            items.append(FeedItem(event=list_item, score=round(score, 3), why_relevant=reasons))
        return sorted(items, key=lambda i: i.score, reverse=True)
