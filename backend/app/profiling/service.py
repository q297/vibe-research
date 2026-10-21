"""ProfilePort implementation backed by CSV files."""

import logging
from pathlib import Path

from app.contracts.clients import ClientProfile, ClientSummary, ClientType, FeedItem
from app.contracts.events import Event
from app.profiling import ranker
from app.profiling.dataset import Dataset, load_dataset
from app.profiling.parsing import parse_client_type
from app.profiling.profiler import (
    LARGE_BUSINESS_BN_RUB,
    build_profile,
    display_name,
    revenue_bn,
)
from app.profiling.sectors import normalize_okved, sector_name

log = logging.getLogger(__name__)

MAX_LISTED_CLIENTS = 500


class CsvProfiles:
    def __init__(
        self,
        data_dir: str | Path,
        *,
        revenue_multiplier: float | None = None,
        large_only: bool = True,
        pinned: list[str] | None = None,
    ) -> None:
        self.dataset: Dataset = load_dataset(Path(data_dir), revenue_multiplier)
        self._large_only = large_only
        self._pinned = [p for p in (pinned or []) if p in self.dataset.companies]
        self._cache: dict[str, ClientProfile] = {}

    def _summary(self, cid: str) -> ClientSummary:
        row = self.dataset.companies[cid]
        okved = normalize_okved(row.get("MAINOKVED_CODE"))
        sector = sector_name(okved)
        ctype = parse_client_type(row.get("CL_TYPE"))
        return ClientSummary(
            client_id=cid,
            display_name=display_name(cid, sector, row.get("REGION")),
            okved_code=okved,
            okved_name=row.get("MAINOKVED_NAME"),
            sector=sector,
            region=row.get("REGION"),
            revenue_bn_rub=revenue_bn(self.dataset, row),
            client_type=ClientType(ctype) if ctype else None,
        )

    async def list_clients(self) -> list[ClientSummary]:
        summaries = [self._summary(cid) for cid in self.dataset.companies]
        if self._large_only:
            large = [s for s in summaries if (s.revenue_bn_rub or 0) >= LARGE_BUSINESS_BN_RUB]
            summaries = large or summaries
        summaries.sort(key=lambda s: -(s.revenue_bn_rub or 0))
        pinned = [self._summary(cid) for cid in self._pinned]
        rest = [s for s in summaries if s.client_id not in set(self._pinned)]
        return (pinned + rest)[:MAX_LISTED_CLIENTS]

    async def get_profile(self, client_id: str) -> ClientProfile | None:
        if client_id not in self._cache:
            profile = build_profile(self.dataset, client_id)
            if profile is None:
                return None
            self._cache[client_id] = profile
        return self._cache[client_id]

    async def rank(self, profile: ClientProfile, events: list[Event]) -> list[FeedItem]:
        return ranker.rank(profile, events)
