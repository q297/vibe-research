"""Builds ClientProfile from CSV data and graphs (rule-based, no LLM)."""

import re
from collections import defaultdict
from dataclasses import dataclass, field

from app.contracts.clients import (
    Affiliate,
    ClientProfile,
    ClientType,
    Counterparty,
    DataQuality,
    DebtLoad,
    ExposureDirection,
    ForeignTrade,
    Product,
    Sensitivity,
)
from app.contracts.taxonomy import TAG_LABELS_RU, SensitivityTag
from app.profiling.countries import parse_countries
from app.profiling.dataset import Dataset, Edge
from app.profiling.parsing import (
    clean,
    gradation_midpoint,
    parse_client_type,
    parse_flag,
    parse_number,
)
from app.profiling.sectors import normalize_okved, sector_name, sector_tags

T = SensitivityTag
D = ExposureDirection

LARGE_BUSINESS_BN_RUB = 15.0
TOP_COUNTERPARTIES = 5
TOP_AFFILIATES = 10
MIN_SENSITIVITY_WEIGHT = 0.25
KEY_COUNTERPARTY_SHARE = 0.3
PASS_THROUGH = 0.6  # a counterparty's exposure reaches the client damped

PRODUCT_COLUMNS: dict[Product, str] = {
    Product.SETTLEMENT: "CL_PRODUCT_RKO_MARK",
    Product.GUARANTEES: "CL_PRODUCT_GAR_MARK",
    Product.CREDIT: "CL_PRODUCT_LOA_MARK",
    Product.LEASING: "CL_PRODUCT_LEA_MARK",
    Product.DEPOSITS: "CL_PRODUCT_DEP_MARK",
    Product.PAYROLL: "CL_PRODUCT_ZPP_MARK",
    Product.FACTORING: "FACTORING_MARK",
}
DEBT_PRODUCTS = (Product.CREDIT, Product.LEASING, Product.FACTORING)

PRODUCT_RULES: dict[Product, list[tuple[T, float, D, str]]] = {
    Product.CREDIT: [
        (T.KEY_RATE, 0.9, D.RISK, "Кредиты: ставка определяет стоимость долга"),
        (T.CREDIT_MARKET, 0.7, D.RISK, "Кредиты: условия рефинансирования"),
    ],
    Product.LEASING: [
        (T.KEY_RATE, 0.8, D.RISK, "Лизинг: платежи привязаны к ставке"),
        (T.CREDIT_MARKET, 0.5, D.RISK, "Лизинг: доступность финансирования"),
    ],
    Product.FACTORING: [
        (T.KEY_RATE, 0.6, D.RISK, "Факторинг: стоимость оборотного финансирования"),
        (T.CREDIT_MARKET, 0.5, D.RISK, "Факторинг: доступность оборотных денег"),
    ],
    Product.DEPOSITS: [
        (T.KEY_RATE, 0.6, D.OPPORTUNITY, "Депозиты: доходность зависит от ставки"),
        (T.BOND_MARKET, 0.4, D.OPPORTUNITY, "Свободная ликвидность: альтернатива депозитам"),
    ],
    Product.GUARANTEES: [
        (T.REGULATION, 0.4, D.MIXED, "Банковские гарантии: госзакупки и контракты"),
    ],
}

STATE_OWNERSHIP_MARKERS = ("государ", "федерал", "муницип", "субъект", "казен")


@dataclass
class _TagAcc:
    weights: list[float] = field(default_factory=list)
    directions: set[D] = field(default_factory=set)
    evidence: list[str] = field(default_factory=list)
    best: tuple[float, str] = (0.0, "")

    def add(self, weight: float, direction: D | None, evidence: str, reason: str) -> None:
        self.weights.append(weight)
        if direction:
            self.directions.add(direction)
        if evidence not in self.evidence:
            self.evidence.append(evidence)
        if weight > self.best[0]:
            self.best = (weight, reason)

    def to_sensitivity(self, tag: T) -> Sensitivity:
        # noisy-OR
        miss = 1.0
        for w in self.weights:
            miss *= 1 - w
        direction = next(iter(self.directions)) if len(self.directions) == 1 else D.MIXED
        return Sensitivity(
            tag=tag,
            weight=round(1 - miss, 3),
            reason=self.best[1],
            direction=direction if self.directions else None,
            evidence=self.evidence,
        )


def lower_first(text: str) -> str:
    """'Металлургия' -> 'металлургия', but 'IT' stays 'IT'"""
    if len(text) > 1 and text[1].isupper():
        return text
    return text[:1].lower() + text[1:]


def display_name(cid: str, sector: str | None, region: str | None) -> str:
    parts = [sector or "Компания"]
    if region:
        parts.append(region.replace(" область", " обл.").replace("Республика ", "Респ. "))
    parts.append("#" + re.sub(r"[^0-9A-Za-zА-Яа-я]", "", cid)[-4:])
    return " · ".join(parts)


def revenue_bn(ds: Dataset, row: dict[str, str | None]) -> float | None:
    value = parse_number(row.get("REVENUE_COMPANY"))
    if value is None or value <= 0:
        return None
    return round(value * ds.revenue_multiplier / 1e9, 2)


def build_profile(ds: Dataset, cid: str) -> ClientProfile | None:
    row = ds.companies.get(cid)
    if row is None:
        return None

    missing: list[str] = []
    notes: list[str] = []
    tags: dict[T, _TagAcc] = defaultdict(_TagAcc)

    okved = normalize_okved(row.get("MAINOKVED_CODE"))
    sector = sector_name(okved)
    if okved is None:
        missing.append("okved")
    elif sector is None:
        notes.append(f"ОКВЭД {okved} нет в справочнике секторов")
    for tag, (weight, direction) in sector_tags(okved).items():
        tags[tag].add(
            weight,
            direction,
            "okved",
            f"{TAG_LABELS_RU[tag]}: ключевой фактор для отрасли «{lower_first(sector)}»",
        )

    region = row.get("REGION")
    if not region:
        missing.append("region")
    revenue = revenue_bn(ds, row)
    if revenue is None:
        missing.append("revenue")
    elif revenue < LARGE_BUSINESS_BN_RUB:
        notes.append(f"Выручка {revenue} млрд ₽ ниже порога крупного бизнеса")

    flags = {p: parse_flag(row.get(col)) for p, col in PRODUCT_COLUMNS.items()}
    products = [p for p, f in flags.items() if f]
    unknown_flags = [p.value for p, f in flags.items() if f is None]
    if unknown_flags:
        missing.append("products")
    for product in products:
        for tag, weight, direction, reason in PRODUCT_RULES.get(product, []):
            tags[tag].add(weight, direction, f"products.{product.value}", reason)

    debt_count = sum(p in products for p in DEBT_PRODUCTS)
    client_type = parse_client_type(row.get("CL_TYPE"))
    if debt_count:
        debt_load = (DebtLoad.LOW, DebtLoad.MEDIUM, DebtLoad.HIGH)[debt_count - 1]
        notes.append("Долговая нагрузка оценена по числу долговых продуктов, сумм долга нет")
    elif client_type == "active" and not any(flags[p] is None for p in DEBT_PRODUCTS):
        debt_load = DebtLoad.NONE
        notes.append("Нет долговых продуктов в Альфа-Банке; долг в других банках не виден")
    else:
        debt_load = None

    employees = gradation_midpoint(row.get("AMOUNT_WORKERS_SPARK_GRADATION"))
    employees_raw = row.get("AMOUNT_WORKERS_SPARK_GRADATION")
    if employees is None:
        employees = gradation_midpoint(row.get("AMOUNT_WORKERS_FNS_GRADATION"))
        employees_raw = row.get("AMOUNT_WORKERS_FNS_GRADATION")
    if employees is None:
        missing.append("employees")
    if Product.PAYROLL in products:
        staff = employees or 0
        weight = 0.4 + min(0.4, staff / 25_000)
        label = f"~{int(staff):,} сотрудников".replace(",", " ") if staff else "штат не известен"
        tags[T.LABOR_MARKET].add(
            weight, D.RISK, "products.payroll", f"Зарплатный проект, {label}: рост ФОТ"
        )

    has_fts = parse_flag(row.get("FTS_FLAG"))
    iso, names = parse_countries(row.get("FTS_COUNTRY_NAME"))
    if names and has_fts is None:
        has_fts = True  # a country is filled, so the company is in FTS data
    if has_fts is None:
        missing.append("foreign_trade")
    if has_fts:
        where = ", ".join(names[:3]) if names else "страна не указана"
        reason = f"ВЭД: {where}"
        sector_fx = sector_tags(okved).get(T.FX_RATE, (0, D.MIXED))[1]
        tags[T.EXPORT_IMPORT].add(0.85, D.MIXED, "foreign_trade", reason)
        tags[T.FX_RATE].add(0.85, sector_fx, "foreign_trade", f"{reason}: валютная выручка/закупки")
        tags[T.SANCTIONS].add(0.5, D.RISK, "foreign_trade", f"{reason}: платежи и санкции")
        tags[T.LOGISTICS].add(0.4, D.RISK, "foreign_trade", f"{reason}: логистика")

    ownership = row.get("OKFS_NAME")
    if ownership and any(m in ownership.lower() for m in STATE_OWNERSHIP_MARKERS):
        tags[T.REGULATION].add(0.5, D.MIXED, "ownership_form", f"Форма собственности: {ownership}")
    if revenue and revenue >= LARGE_BUSINESS_BN_RUB:
        tags[T.ECONOMIC_GROWTH].add(
            0.4, D.OPPORTUNITY, "revenue", "Крупный бизнес: выручка следует за циклом экономики"
        )
    counterparties, hhi = _counterparties(ds, cid)
    if not ds.has_payments:
        notes.append("Платежи не загружены")
    elif not counterparties:
        notes.append("Нет платежей с контрагентами")
    else:
        for cp in counterparties:
            if not cp.share or cp.share < KEY_COUNTERPARTY_SHARE or not cp.sector:
                continue
            # second-order exposure via a key counterparty
            passed = sorted(
                (
                    (t, w)
                    for t, (w, _) in sector_tags(cp.okved_code).items()
                    if t not in (T.KEY_RATE, T.CREDIT_MARKET)
                ),
                key=lambda tw: -tw[1],
            )[:3]
            who = "поставщик" if cp.role == "supplier" else "покупатель"
            flow = "закупок" if cp.role == "supplier" else "поступлений"
            for tag, weight in passed:
                tags[tag].add(
                    round(weight * cp.share * PASS_THROUGH, 3),
                    D.RISK,
                    f"counterparty.{cp.counterparty_id}",
                    f"{TAG_LABELS_RU[tag]}: через ключевого {who}а "
                    f"({lower_first(cp.sector)}, {cp.share:.0%} {flow})",
                )

    sensitivities = sorted(
        (acc.to_sensitivity(tag) for tag, acc in tags.items()),
        key=lambda s: s.weight,
        reverse=True,
    )
    sensitivities = [s for s in sensitivities if s.weight >= MIN_SENSITIVITY_WEIGHT]

    key_fields = ["okved", "region", "revenue", "employees", "products", "foreign_trade"]
    known = sum(f not in missing for f in key_fields)
    if client_type is None:
        missing.append("client_type")

    return ClientProfile(
        client_id=cid,
        display_name=display_name(cid, sector, region),
        okved_code=okved,
        okved_name=row.get("MAINOKVED_NAME"),
        sector=sector,
        region=region,
        revenue_bn_rub=revenue,
        client_type=ClientType(client_type) if client_type else None,
        company_age_years=gradation_midpoint(row.get("COMPANY_AGE_YEARS_GRADATION")),
        company_age_gradation=row.get("COMPANY_AGE_YEARS_GRADATION"),
        employees=int(employees) if employees is not None else None,
        employees_gradation=employees_raw,
        org_type=row.get("ORG_TYPE"),
        ownership_form=ownership,
        business_stage=row.get("ECO_MARK_LABEL"),
        key_owner_mark=parse_flag(row.get("NEGATIVEMARK")),
        group_id=row.get("GROUP_ID"),
        city=row.get("CITY"),
        products=products,
        debt_load=debt_load,
        foreign_trade=ForeignTrade(has_fea=has_fts, countries=iso, country_names=names),
        sensitivities=sensitivities,
        top_counterparties=counterparties[: TOP_COUNTERPARTIES * 2],
        counterparty_concentration=hhi,
        affiliates=_affiliates(ds, cid, row.get("GROUP_ID")),
        data_quality=DataQuality(
            missing_fields=missing,
            notes=notes + ds.notes,
            completeness=round(known / len(key_fields), 2),
        ),
    )


def _counterparty(ds: Dataset, edge: Edge, role: str, total: float) -> Counterparty:
    other = ds.companies.get(edge.counterparty, {})
    okved = normalize_okved(other.get("MAINOKVED_CODE"))
    return Counterparty(
        counterparty_id=edge.counterparty,
        okved_code=okved,
        okved_name=clean(other.get("MAINOKVED_NAME")),
        sector=sector_name(okved),
        role=role,
        share=round(edge.amount / total, 4) if total else None,
        payments_count=edge.count or None,
        tags=list(sector_tags(okved)),
    )


def _counterparties(ds: Dataset, cid: str) -> tuple[list[Counterparty], float | None]:
    out_edges = ds.outgoing.get(cid, [])
    in_edges = ds.incoming.get(cid, [])
    out_total = sum(e.amount for e in out_edges)
    in_total = sum(e.amount for e in in_edges)
    result = [_counterparty(ds, e, "supplier", out_total) for e in out_edges[:TOP_COUNTERPARTIES]]
    result += [_counterparty(ds, e, "buyer", in_total) for e in in_edges[:TOP_COUNTERPARTIES]]
    result.sort(key=lambda c: c.share or 0, reverse=True)

    volume: dict[str, float] = defaultdict(float)
    for e in (*out_edges, *in_edges):
        volume[e.counterparty] += e.amount
    total = sum(volume.values())
    hhi = round(sum((v / total) ** 2 for v in volume.values()), 4) if total else None
    return result, hhi


def _affiliates(ds: Dataset, cid: str, group_id: str | None) -> list[Affiliate]:
    found: dict[str, Affiliate] = {}
    if group_id:
        for other in ds.groups.get(group_id, ()):
            if other != cid:
                found[other] = Affiliate(client_id=other, link="group")
    shared: dict[str, int] = defaultdict(int)
    for person in ds.persons_by_company.get(cid, ()):
        for other in ds.companies_by_person.get(person, ()):
            if other != cid:
                shared[other] += 1
    for other, n in shared.items():
        if other in found:
            found[other].shared_persons = n
        else:
            found[other] = Affiliate(client_id=other, link="person", shared_persons=n)
    for aff in found.values():
        aff.sector = sector_name(ds.companies.get(aff.client_id, {}).get("MAINOKVED_CODE"))
    ranked = sorted(found.values(), key=lambda a: (a.link == "group", a.shared_persons))
    return list(reversed(ranked))[:TOP_AFFILIATES]
