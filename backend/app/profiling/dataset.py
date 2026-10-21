"""Loads case CSVs (detected by columns) and builds payment/person graphs."""

import csv
import io
import logging
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from app.profiling.parsing import clean, parse_number

log = logging.getLogger(__name__)

COMPANY_KEY_COLUMNS = {"SYNTHETIC_U", "MAINOKVED_CODE"}
PERSON_KEY_COLUMNS = {"SYNTHETIC_F", "SYNTHETIC_U"}
PAYMENT_KEY_COLUMNS = {"PAYER", "BENEFICIARY"}

# Persons linked to more companies are treated as noise
MAX_COMPANIES_PER_PERSON = 50


@dataclass
class Edge:
    counterparty: str
    amount: float
    count: int


@dataclass
class Dataset:
    companies: dict[str, dict[str, str | None]] = field(default_factory=dict)
    outgoing: dict[str, list[Edge]] = field(default_factory=lambda: defaultdict(list))
    incoming: dict[str, list[Edge]] = field(default_factory=lambda: defaultdict(list))
    persons_by_company: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    companies_by_person: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    groups: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    revenue_multiplier: float = 1.0
    notes: list[str] = field(default_factory=list)

    @property
    def has_payments(self) -> bool:
        return bool(self.outgoing or self.incoming)

    @property
    def has_persons(self) -> bool:
        return bool(self.persons_by_company)


def _open_csv(path: Path) -> tuple[csv.DictReader, io.TextIOBase]:
    with path.open("rb") as f:
        head = f.read(256_000)
    encoding = "utf-8-sig"
    try:
        head[: head.rfind(b"\n") + 1 or None].decode("utf-8-sig")
    except UnicodeDecodeError:
        encoding = "cp1251"
    sample = head.decode(encoding, errors="replace")[:20_000]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    handle = path.open(encoding=encoding, errors="replace", newline="")
    reader = csv.DictReader(handle, dialect=dialect)
    if reader.fieldnames:
        reader.fieldnames = [(f or "").strip().upper() for f in reader.fieldnames]
    return reader, handle


def _kind(columns: set[str]) -> str | None:
    if PAYMENT_KEY_COLUMNS <= columns:
        return "payments"
    if COMPANY_KEY_COLUMNS <= columns:
        return "companies"
    if PERSON_KEY_COLUMNS <= columns:
        return "persons"
    return None


def detect_revenue_multiplier(values: list[float]) -> tuple[float, str]:
    """Guess REVENUE_COMPANY units from the median."""
    positive = [v for v in values if v > 0]
    if not positive:
        return 1.0, "Выручка не заполнена ни у одной компании"
    med = statistics.median(positive)
    if med >= 1e8:
        return 1.0, f"Выручка трактуется в рублях (медиана {med:,.0f})"
    if med >= 1e5:
        return 1e3, f"Выручка трактуется в тыс. руб. (медиана {med:,.0f})"
    if med >= 1e2:
        return 1e6, f"Выручка трактуется в млн руб. (медиана {med:,.0f})"
    return 1e9, f"Выручка трактуется в млрд руб. (медиана {med:,.2f})"


def load_dataset(data_dir: Path, revenue_multiplier: float | None = None) -> Dataset:
    ds = Dataset()
    files = sorted(p for p in data_dir.glob("*.csv") if p.is_file())
    if not files:
        raise FileNotFoundError(f"No CSV files in {data_dir}")

    pair_amount: dict[tuple[str, str], list[float]] = defaultdict(lambda: [0.0, 0])
    skipped = 0
    for path in files:
        reader, handle = _open_csv(path)
        with handle:
            kind = _kind(set(reader.fieldnames or []))
            if kind is None:
                log.warning("Skip %s: unknown columns %s", path.name, reader.fieldnames)
                continue
            log.info("Load %s as %s", path.name, kind)
            skipped += _consume(reader, kind, ds, pair_amount)

    for (payer, benef), (amount, count) in pair_amount.items():
        ds.outgoing[payer].append(Edge(benef, amount, count))
        ds.incoming[benef].append(Edge(payer, amount, count))
    for edges in (*ds.outgoing.values(), *ds.incoming.values()):
        edges.sort(key=lambda e: e.amount, reverse=True)

    noisy = [p for p, cs in ds.companies_by_person.items() if len(cs) > MAX_COMPANIES_PER_PERSON]
    for person in noisy:
        for cid in ds.companies_by_person.pop(person):
            ds.persons_by_company[cid].discard(person)
    if noisy:
        ds.notes.append(
            f"Отброшено {len(noisy)} физлиц, связанных с >{MAX_COMPANIES_PER_PERSON} компаниями"
        )

    for cid, row in ds.companies.items():
        if gid := row.get("GROUP_ID"):
            ds.groups[gid].add(cid)

    revenues = [v for r in ds.companies.values() if (v := parse_number(r.get("REVENUE_COMPANY")))]
    if revenue_multiplier is None:
        ds.revenue_multiplier, note = detect_revenue_multiplier(revenues)
    else:
        ds.revenue_multiplier, note = revenue_multiplier, f"Множитель выручки {revenue_multiplier}"
    ds.notes.append(note)
    if skipped:
        ds.notes.append(f"Пропущено {skipped} строк без ключевых полей")
    log.info(
        "Dataset: %d companies, %d payment pairs, %d persons. %s",
        len(ds.companies),
        len(pair_amount),
        len(ds.companies_by_person),
        "; ".join(ds.notes),
    )
    return ds


def _consume(
    reader: csv.DictReader, kind: str, ds: Dataset, pair_amount: dict[tuple[str, str], list]
) -> int:
    skipped = 0
    for row in reader:
        if kind == "companies":
            cid = clean(row.get("SYNTHETIC_U"))
            if not cid:
                skipped += 1
                continue
            values = {k: clean(v) for k, v in row.items() if k}
            prev = ds.companies.get(cid)
            if prev is None or _filled(values) > _filled(prev):
                ds.companies[cid] = values
        elif kind == "persons":
            fid, cid = clean(row.get("SYNTHETIC_F")), clean(row.get("SYNTHETIC_U"))
            if fid and cid:
                ds.persons_by_company[cid].add(fid)
                ds.companies_by_person[fid].add(cid)
            else:
                skipped += 1
        else:
            payer, benef = clean(row.get("PAYER")), clean(row.get("BENEFICIARY"))
            amount = parse_number(row.get("PAY_AMT"))
            count = parse_number(row.get("PAY_CNT"))
            if not payer or not benef or payer == benef or amount is None or amount <= 0:
                skipped += 1
                continue
            acc = pair_amount[(payer, benef)]
            acc[0] += amount
            acc[1] += int(count or 0)
    return skipped


def _filled(row: dict[str, str | None]) -> int:
    return sum(v is not None for v in row.values())
