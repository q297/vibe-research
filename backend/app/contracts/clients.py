"""Client profile and personalized feed produced by role 3"""

from enum import StrEnum

from pydantic import Field

from app.contracts.common import Contract, Page
from app.contracts.events import EventListItem
from app.contracts.insights import InsightStatus
from app.contracts.taxonomy import SensitivityTag


class ClientType(StrEnum):
    ACTIVE = "active"
    POTENTIAL = "potential"


class Product(StrEnum):
    SETTLEMENT = "settlement"
    GUARANTEES = "guarantees"
    CREDIT = "credit"
    LEASING = "leasing"
    DEPOSITS = "deposits"
    PAYROLL = "payroll"
    FACTORING = "factoring"


class DebtLoad(StrEnum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ClientSummary(Contract):
    client_id: str
    display_name: str = Field(description="Synthetic alias, data is anonymized")
    okved_code: str | None = None
    okved_name: str | None = None
    region: str | None = None
    revenue_bn_rub: float | None = None
    client_type: ClientType | None = None


class Sensitivity(Contract):
    tag: SensitivityTag
    weight: float = Field(ge=0, le=1)
    reason: str = Field(description="Human readable, shown in the 'why relevant' chips")


class Counterparty(Contract):
    counterparty_id: str
    okved_code: str | None = None
    okved_name: str | None = None
    role: str = Field(description="supplier or buyer")
    share: float | None = Field(default=None, ge=0, le=1, description="Share of payment volume")


class ForeignTrade(Contract):
    has_fea: bool | None = Field(default=None, description="None means unknown, not 'no' (D8)")
    countries: list[str] = Field(default_factory=list)


class ClientProfile(ClientSummary):
    company_age_years: float | None = None
    employees: int | None = None
    group_id: str | None = None
    city: str | None = None
    products: list[Product] = Field(default_factory=list)
    debt_load: DebtLoad | None = None
    foreign_trade: ForeignTrade = Field(default_factory=ForeignTrade)
    sensitivities: list[Sensitivity] = Field(default_factory=list)
    top_counterparties: list[Counterparty] = Field(default_factory=list)


class RelevanceReason(Contract):
    feature: str = Field(description="Profile feature key, e.g. 'products.credit'")
    label: str
    tag: SensitivityTag | None = None


class FeedItem(Contract):
    event: EventListItem
    score: float = Field(description="Personal score, comparable only within one feed")
    why_relevant: list[RelevanceReason] = Field(default_factory=list)
    insight_status: InsightStatus | None = Field(
        default=None, description="Status of the cached insight for this pair, if any"
    )


class FeedPage(Page[FeedItem]):
    pass
