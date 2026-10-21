"""Feed ranking: score = sum(reason weights) * importance * freshness."""

from datetime import UTC, datetime

from app.contracts.clients import ClientProfile, FeedItem, RelevanceReason
from app.contracts.events import Event, EventListItem
from app.contracts.taxonomy import TAG_LABELS_RU, SensitivityTag
from app.profiling.countries import iso_name
from app.profiling.profiler import lower_first

W_TAG = 1.0  # times sensitivity weight, for the strongest matching tag
TAG_DECAY = (1.0, 0.5, 0.25)  # 2nd and 3rd matching tags add less: many tags != relevance
W_OKVED_EXACT = 0.8
W_OKVED_SECTION = 0.5
W_COUNTERPARTY_OKVED = 0.6  # times (0.5 + share)
W_COUNTERPARTY_TAG = 0.5  # times share, only for tags the client itself lacks
W_COUNTRY = 0.6
W_REGION = 0.3
W_ECONOMY_WIDE = 0.1
OFF_SECTOR_FACTOR = 0.35
MIN_RELEVANCE = 0.2
MIN_COUNTERPARTY_SHARE = 0.05
MIN_REASON_WEIGHT = 0.08  # weaker side signals are noise in the chips
FRESHNESS_HALF_LIFE_DAYS = 10
FRESHNESS_FLOOR = 0.25


def _okved_match(code: str | None, sections: list[str]) -> str | None:
    if not code:
        return None
    best = None
    for s in sections:
        s = s.strip()
        if not s or s == "*":
            continue
        if code.startswith(s) and len(s) > 2:
            return "exact"
        if code[:2] == s[:2]:
            best = "section"
    return best


def _cp_words(role: str) -> tuple[str, str, str]:
    if role == "supplier":
        return "поставщик", "поставщика", "закупок"
    return "покупатель", "покупателя", "поступлений"


def explain(profile: ClientProfile, event: Event) -> list[RelevanceReason]:
    reasons: list[RelevanceReason] = []
    sens = {s.tag: s for s in profile.sensitivities}
    event_tags = [t for t in event.tags if t != SensitivityTag.OTHER]
    cps = [cp for cp in profile.top_counterparties if (cp.share or 0) >= MIN_COUNTERPARTY_SHARE]

    match = _okved_match(profile.okved_code, event.okved_sections)
    cp_hits = [cp for cp in cps if _okved_match(cp.okved_code, event.okved_sections)]
    # discount events aimed at other industries
    sections = [s for s in event.okved_sections if s.strip()]
    off_sector = bool(sections) and "*" not in sections and not match and not cp_hits
    factor = OFF_SECTOR_FACTOR if off_sector else 1.0

    matched = sorted((sens[t] for t in event_tags if t in sens), key=lambda s: -s.weight)
    for decay, s in zip(TAG_DECAY, matched, strict=False):
        feature = s.evidence[0] if s.evidence else f"sensitivity.{s.tag.value}"
        reasons.append(
            RelevanceReason(
                feature=feature,
                label=s.reason,
                tag=s.tag,
                weight=round(W_TAG * s.weight * decay * factor, 3),
            )
        )

    if match:
        sector = profile.sector or profile.okved_name or ""
        reasons.append(
            RelevanceReason(
                feature="okved",
                label=f"Новость о вашей отрасли: {lower_first(sector)}",
                weight=W_OKVED_EXACT if match == "exact" else W_OKVED_SECTION,
            )
        )

    cp_reasons: list[RelevanceReason] = []
    for cp in cps:
        share = cp.share or 0
        who, whom, flow = _cp_words(cp.role)
        what = lower_first(cp.sector or cp.okved_name or "отрасль не известна")
        if cp in cp_hits:
            cp_reasons.append(
                RelevanceReason(
                    feature=f"counterparty.{cp.counterparty_id}",
                    label=f"Затронут ваш {who}: {what}, {share:.0%} {flow}",
                    weight=round(W_COUNTERPARTY_OKVED * min(1.0, 0.3 + share), 3),
                )
            )
            continue
        shared = [t for t in event_tags if t in cp.tags and t not in sens]
        if shared and share >= 0.1 and W_COUNTERPARTY_TAG * share * factor >= MIN_REASON_WEIGHT:
            cp_reasons.append(
                RelevanceReason(
                    feature=f"counterparty.{cp.counterparty_id}",
                    label=f"{TAG_LABELS_RU[shared[0]]}: через {whom} ({what}, {share:.0%} {flow})",
                    tag=shared[0],
                    weight=round(W_COUNTERPARTY_TAG * share * factor, 3),
                )
            )
    reasons += sorted(cp_reasons, key=lambda r: -(r.weight or 0))[:2]

    common = [c for c in event.countries if c in profile.foreign_trade.countries]
    if common:
        names = ", ".join(iso_name(c) for c in common[:3])
        reasons.append(
            RelevanceReason(
                feature="foreign_trade.countries",
                label=f"Страна вашей ВЭД: {names}",
                tag=SensitivityTag.EXPORT_IMPORT,
                weight=W_COUNTRY,
            )
        )

    if profile.region and profile.region in event.regions:
        reasons.append(
            RelevanceReason(
                feature="region", label=f"Ваш регион: {profile.region}", weight=W_REGION
            )
        )

    if reasons and "*" in event.okved_sections:
        reasons.append(
            RelevanceReason(feature="macro", label="Касается всей экономики", weight=W_ECONOMY_WIDE)
        )
    return _merge_same_labels(reasons)


def _merge_same_labels(reasons: list[RelevanceReason]) -> list[RelevanceReason]:
    merged: dict[str, RelevanceReason] = {}
    for r in reasons:
        if r.label in merged:
            prev = merged[r.label]
            prev.weight = round((prev.weight or 0) + (r.weight or 0), 3)
        else:
            merged[r.label] = r.model_copy()
    return list(merged.values())


def freshness(event: Event, now: datetime) -> float:
    ts = event.published_at or event.ingested_at
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    age_days = max(0.0, (now - ts).total_seconds() / 86_400)
    return max(FRESHNESS_FLOOR, 0.5 ** (age_days / FRESHNESS_HALF_LIFE_DAYS))


def rank(
    profile: ClientProfile, events: list[Event], *, now: datetime | None = None
) -> list[FeedItem]:
    now = now or datetime.now(UTC)
    items: list[FeedItem] = []
    for event in events:
        if event.merged_into:
            continue
        reasons = explain(profile, event)
        relevance = sum(r.weight or 0 for r in reasons)
        if relevance < MIN_RELEVANCE:
            continue
        importance = event.importance if event.importance is not None else 0.5
        score = relevance * (0.5 + importance) * freshness(event, now)
        list_item = EventListItem.model_validate(
            event.model_dump(exclude={"entities", "articles"})
            | {"source_count": max(1, len(event.articles))}
        )
        reasons.sort(key=lambda r: -(r.weight or 0))
        items.append(FeedItem(event=list_item, score=round(score, 4), why_relevant=reasons))
    items.sort(key=lambda i: (-i.score, i.event.event_id))
    return items
