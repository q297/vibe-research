"""Client profile and personalized feed (role 3)."""

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


class ExposureDirection(StrEnum):
    RISK = "risk"
    OPPORTUNITY = "opportunity"
    MIXED = "mixed"


class ClientSummary(Contract):
    client_id: str
    display_name: str = Field(description="Synthetic alias, data is anonymized")
    okved_code: str | None = None
    okved_name: str | None = None
    sector: str | None = Field(default=None, description="Enlarged sector derived from OKVED")
    region: str | None = None
    revenue_bn_rub: float | None = None
    client_type: ClientType | None = None


class Sensitivity(Contract):
    tag: SensitivityTag
    weight: float = Field(ge=0, le=1)
    reason: str = Field(description="Human readable, shown in the 'why relevant' chips")
    direction: ExposureDirection | None = None
    evidence: list[str] = Field(
        default_factory=list,
        description="Profile feature keys that produced the tag, e.g. 'products.credit' (crit. 12)",
    )


class Counterparty(Contract):
    counterparty_id: str
    okved_code: str | None = None
    okved_name: str | None = None
    sector: str | None = None
    role: str = Field(description="supplier or buyer")
    share: float | None = Field(default=None, ge=0, le=1, description="Share of payment volume")
    payments_count: int | None = None
    tags: list[SensitivityTag] = Field(
        default_factory=list, description="Sector tags of the counterparty, for 2nd-order impact"
    )


class Affiliate(Contract):
    client_id: str
    link: str = Field(description="group or person")
    shared_persons: int = 0
    sector: str | None = None


class ForeignTrade(Contract):
    has_fea: bool | None = Field(default=None, description="None means unknown, not 'no' (D8)")
    countries: list[str] = Field(default_factory=list, description="ISO 3166-1 alpha-2 (D4)")
    country_names: list[str] = Field(default_factory=list, description="As written in FTS data")


class DataQuality(Contract):
    missing_fields: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    completeness: float = Field(default=1.0, ge=0, le=1, description="Share of key fields known")


class ClientProfile(ClientSummary):
    company_age_years: float | None = Field(default=None, description="Midpoint of the gradation")
    company_age_gradation: str | None = Field(default=None, description="Raw value from CSV")
    employees: int | None = Field(default=None, description="Midpoint of the gradation")
    employees_gradation: str | None = None
    org_type: str | None = None
    ownership_form: str | None = Field(default=None, description="OKFS_NAME")
    business_stage: str | None = Field(default=None, description="ECO_MARK_LABEL")
    key_owner_mark: bool | None = Field(default=None, description="NEGATIVEMARK")
    group_id: str | None = None
    city: str | None = None
    products: list[Product] = Field(default_factory=list)
    debt_load: DebtLoad | None = None
    foreign_trade: ForeignTrade = Field(default_factory=ForeignTrade)
    sensitivities: list[Sensitivity] = Field(default_factory=list)
    top_counterparties: list[Counterparty] = Field(default_factory=list)
    counterparty_concentration: float | None = Field(
        default=None, ge=0, le=1, description="HHI of payment volume over all counterparties"
    )
    affiliates: list[Affiliate] = Field(default_factory=list)
    data_quality: DataQuality = Field(default_factory=DataQuality)


class RelevanceReason(Contract):
    feature: str = Field(description="Profile feature key, e.g. 'products.credit'")
    label: str
    tag: SensitivityTag | None = None
    weight: float | None = Field(
        default=None, description="Contribution to the score before freshness and importance"
    )


class FeedItem(Contract):
    event: EventListItem
    score: float = Field(description="Personal score, comparable only within one feed")
    why_relevant: list[RelevanceReason] = Field(default_factory=list)
    insight_status: InsightStatus | None = Field(
        default=None, description="Status of the cached insight for this pair, if any"
    )


class FeedPage(Page[FeedItem]):
    pass
