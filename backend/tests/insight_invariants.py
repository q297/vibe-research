"""Invariants every Insight must hold, agreed with role 4; reuse them in agent tests"""

from app.contracts.common import CitationKind, Provenance
from app.contracts.insights import Insight, InsightStatus

FACT_SOURCES = {CitationKind.ARTICLE, CitationKind.USER_INPUT}


def insight_violations(insight: Insight) -> list[str]:
    problems: list[str] = []
    if insight.status != InsightStatus.READY:
        return problems

    claims = [*insight.what_happened, *insight.why_it_matters, *insight.scenarios]
    claims += [item.claim for item in [*insight.risks, *insight.opportunities]]
    for claim in claims:
        kinds = {c.kind for c in claim.citations}
        if claim.provenance == Provenance.SOURCE_FACT and not kinds & FACT_SOURCES:
            problems.append(f"source_fact without article citation: {claim.text[:60]}")
        if claim.provenance == Provenance.BANK_POSITION and CitationKind.BANK_DOC not in kinds:
            problems.append(f"bank_position without bank_doc citation: {claim.text[:60]}")

    for claim in insight.what_happened:
        if claim.provenance != Provenance.SOURCE_FACT:
            problems.append(f"what_happened must be source_fact: {claim.text[:60]}")

    for claim in insight.why_it_matters:
        features = [c.source_id for c in claim.citations if c.kind == CitationKind.CLIENT_DATA]
        if not features:
            problems.append(f"why_it_matters without client feature: {claim.text[:60]}")
        missing = set(features) - set(insight.client_features_used)
        if missing:
            problems.append(f"features not in client_features_used: {sorted(missing)}")

    if not insight.bank_positions and not insight.data_gaps:
        problems.append("no bank position and no data gap explaining why")
    return problems
