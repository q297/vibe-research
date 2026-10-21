"""Generate synthetic CSVs in the case format: python -m scripts.gen_synthetic_clients"""

import csv
import random
from pathlib import Path

OUT = Path(__file__).parents[1] / "app/profiling/synthetic_data"
SEED = 2026

COMPANY_COLUMNS = [
    "SYNTHETIC_U", "ORG_TYPE", "OKFS_NAME", "COMPANY_AGE_YEARS_GRADATION", "ECO_MARK_LABEL",
    "MAINOKVED_CODE", "MAINOKVED_NAME", "NEGATIVEMARK", "AMOUNT_WORKERS_FNS_GRADATION",
    "AMOUNT_WORKERS_SPARK_GRADATION", "CL_TYPE", "CL_PRODUCT_RKO_MARK", "CL_PRODUCT_GAR_MARK",
    "CL_PRODUCT_LOA_MARK", "CL_PRODUCT_LEA_MARK", "CL_PRODUCT_DEP_MARK", "CL_PRODUCT_ZPP_MARK",
    "FTS_FLAG", "FTS_COUNTRY_NAME", "FACTORING_MARK", "REVENUE_COMPANY", "GROUP_ID", "CITY",
    "REGION",
]  # fmt: skip

OKVED = {
    "24.10": "Производство чугуна, стали и ферросплавов",
    "47.11": "Торговля розничная преимущественно пищевыми продуктами в неспециализированных магазинах",
    "01.11": "Выращивание зерновых культур",
    "41.20": "Строительство жилых и нежилых зданий",
    "46.71": "Торговля оптовая твердым, жидким и газообразным топливом",
    "62.01": "Разработка компьютерного программного обеспечения",
    "05.10": "Добыча и обогащение угля и антрацита",
    "49.20": "Деятельность железнодорожного транспорта: грузовые перевозки",
    "35.11": "Производство электроэнергии",
    "10.51": "Производство молочной продукции",
    "10.11": "Переработка и консервирование мяса",
    "46.39": "Торговля оптовая неспециализированная пищевыми продуктами",
    "23.51": "Производство цемента",
    "24.20": "Производство стальных труб",
    "20.15": "Производство удобрений и азотных соединений",
    "28.30": "Производство машин и оборудования для сельского и лесного хозяйства",
    "52.10": "Деятельность по складированию и хранению",
    "06.10": "Добыча нефти",
    "19.20": "Производство нефтепродуктов",
    "68.20": "Аренда и управление собственным или арендованным недвижимым имуществом",
    "64.19": "Денежное посредничество прочее",
    "45.11": "Торговля легковыми автомобилями",
    "29.10": "Производство автотранспортных средств",
    "71.12": "Деятельность в области инженерных изысканий",
    "16.10": "Распиловка и строгание древесины",
}

REGIONS = [
    ("Москва", "Москва"), ("Санкт-Петербург", "Санкт-Петербург"),
    ("Екатеринбург", "Свердловская область"), ("Краснодар", "Краснодарский край"),
    ("Новосибирск", "Новосибирская область"), ("Казань", "Республика Татарстан"),
    ("Челябинск", "Челябинская область"), ("Кемерово", "Кемеровская область"),
    ("Нижний Новгород", "Нижегородская область"), ("Ростов-на-Дону", "Ростовская область"),
]  # fmt: skip

WORKERS = ["до 100", "100-250", "251-1000", "1001-5000", "свыше 5000"]
AGES = ["до 3 лет", "3-10 лет", "10-20 лет", "свыше 20 лет"]
STAGES = ["Рост", "Зрелость", "Стабильность", "Спад"]
OKFS = ["Частная собственность", "Смешанная российская собственность",
        "Федеральная собственность", "Иностранная собственность"]  # fmt: skip


def company(cid: str, okved: str, city_region: tuple[str, str], revenue_bn: float, **kw) -> dict:
    city, region = city_region
    row = {
        "SYNTHETIC_U": cid, "ORG_TYPE": "ЮЛ", "OKFS_NAME": "Частная собственность",
        "COMPANY_AGE_YEARS_GRADATION": "10-20 лет", "ECO_MARK_LABEL": "Зрелость",
        "MAINOKVED_CODE": okved, "MAINOKVED_NAME": OKVED.get(okved, ""), "NEGATIVEMARK": "0",
        "AMOUNT_WORKERS_FNS_GRADATION": "1001-5000", "AMOUNT_WORKERS_SPARK_GRADATION": "1001-5000",
        "CL_TYPE": "Действующий", "CL_PRODUCT_RKO_MARK": "1", "CL_PRODUCT_GAR_MARK": "0",
        "CL_PRODUCT_LOA_MARK": "0", "CL_PRODUCT_LEA_MARK": "0", "CL_PRODUCT_DEP_MARK": "0",
        "CL_PRODUCT_ZPP_MARK": "0", "FTS_FLAG": "0", "FTS_COUNTRY_NAME": "",
        "FACTORING_MARK": "0", "REVENUE_COMPANY": f"{revenue_bn * 1e9:.0f}", "GROUP_ID": "",
        "CITY": city, "REGION": region,
    }  # fmt: skip
    row.update(kw)
    return row


DEMO = [
    company("c-001", "24.10", REGIONS[2], 48.5, CL_PRODUCT_LOA_MARK="1", CL_PRODUCT_LEA_MARK="1",
            CL_PRODUCT_GAR_MARK="1", CL_PRODUCT_ZPP_MARK="1", FTS_FLAG="1",
            FTS_COUNTRY_NAME="Китай; Турция", AMOUNT_WORKERS_SPARK_GRADATION="свыше 5000",
            COMPANY_AGE_YEARS_GRADATION="свыше 20 лет", GROUP_ID="g-101"),
    company("c-002", "47.11", REGIONS[0], 22.1, CL_PRODUCT_DEP_MARK="1", CL_PRODUCT_ZPP_MARK="1",
            AMOUNT_WORKERS_SPARK_GRADATION="свыше 5000", COMPANY_AGE_YEARS_GRADATION="10-20 лет"),
    company("c-003", "01.11", REGIONS[3], 17.4, CL_PRODUCT_LOA_MARK="1", FACTORING_MARK="1",
            FTS_FLAG="1", FTS_COUNTRY_NAME="Египет", ECO_MARK_LABEL="Рост"),
    company("c-004", "41.20", REGIONS[0], 35.2, CL_PRODUCT_LOA_MARK="1", CL_PRODUCT_GAR_MARK="1",
            CL_PRODUCT_ZPP_MARK="1", GROUP_ID="g-204"),
    company("c-005", "46.71", REGIONS[5], 27.9, CL_TYPE="Потенциальный", CL_PRODUCT_RKO_MARK="",
            CL_PRODUCT_LOA_MARK="", CL_PRODUCT_LEA_MARK="", CL_PRODUCT_DEP_MARK="",
            CL_PRODUCT_ZPP_MARK="", CL_PRODUCT_GAR_MARK="", FACTORING_MARK="",
            FTS_FLAG="", FTS_COUNTRY_NAME="Казахстан", AMOUNT_WORKERS_SPARK_GRADATION=""),
    company("c-006", "62.01", REGIONS[1], 16.3, OKFS_NAME="Смешанная российская собственность",
            CL_PRODUCT_DEP_MARK="да", CL_PRODUCT_ZPP_MARK="да", CL_PRODUCT_RKO_MARK="да",
            AMOUNT_WORKERS_SPARK_GRADATION="1001-5000", ECO_MARK_LABEL="Рост"),
]  # fmt: skip
DEMO_LINKS = [
    ("c-001", "05.10", "supplier", 0.38), ("c-001", "49.20", "supplier", 0.14),
    ("c-001", "35.11", "supplier", 0.10), ("c-001", "24.20", "buyer", 0.30),
    ("c-001", "46.39", "buyer", 0.05),
    ("c-002", "10.51", "supplier", 0.22), ("c-002", "10.11", "supplier", 0.18),
    ("c-002", "46.39", "supplier", 0.25), ("c-002", "52.10", "supplier", 0.08),
    ("c-003", "20.15", "supplier", 0.35), ("c-003", "28.30", "supplier", 0.20),
    ("c-003", "46.39", "buyer", 0.45), ("c-003", "52.10", "supplier", 0.10),
    ("c-004", "23.51", "supplier", 0.42), ("c-004", "24.20", "supplier", 0.12),
    ("c-004", "71.12", "supplier", 0.08), ("c-004", "68.20", "buyer", 0.20),
    ("c-005", "19.20", "supplier", 0.55), ("c-005", "49.20", "supplier", 0.15),
    ("c-005", "35.11", "buyer", 0.25),
    ("c-006", "64.19", "buyer", 0.30), ("c-006", "68.20", "supplier", 0.15),
]  # fmt: skip


def noisy_flag(rng: random.Random, value: bool) -> str:
    if rng.random() < 0.05:
        return ""
    return rng.choice(["1", "1.0", "Y", "да"] if value else ["0", "0.0", "N", "нет"])


def background(rng: random.Random, n: int) -> list[dict]:
    rows = []
    codes = list(OKVED)
    for i in range(n):
        cid = f"u-{i:05d}"
        okved = rng.choice(codes)
        revenue = rng.lognormvariate(23.2, 1.3)  # median ~12 bn RUB, long tail
        fea = rng.random() < 0.25
        row = company(
            cid, okved, rng.choice(REGIONS), revenue / 1e9,
            OKFS_NAME=rng.choice(OKFS), ECO_MARK_LABEL=rng.choice(STAGES),
            COMPANY_AGE_YEARS_GRADATION=rng.choice(AGES),
            AMOUNT_WORKERS_FNS_GRADATION=rng.choice(WORKERS),
            AMOUNT_WORKERS_SPARK_GRADATION=rng.choice(WORKERS + [""]),
            CL_TYPE=rng.choice(["Действующий", "Действующий", "Потенциальный"]),
            CL_PRODUCT_LOA_MARK=noisy_flag(rng, rng.random() < 0.5),
            CL_PRODUCT_LEA_MARK=noisy_flag(rng, rng.random() < 0.3),
            CL_PRODUCT_DEP_MARK=noisy_flag(rng, rng.random() < 0.4),
            CL_PRODUCT_ZPP_MARK=noisy_flag(rng, rng.random() < 0.4),
            CL_PRODUCT_GAR_MARK=noisy_flag(rng, rng.random() < 0.2),
            FACTORING_MARK=noisy_flag(rng, rng.random() < 0.15),
            FTS_FLAG="1" if fea else rng.choice(["0", ""]),
            FTS_COUNTRY_NAME=rng.choice(["Китай", "Турция", "Казахстан", "ОАЭ", "Индия",
                                         "Беларусь", "Узбекистан"]) if fea else "",
            GROUP_ID=f"g-{rng.randint(300, 340)}" if rng.random() < 0.2 else "",
        )  # fmt: skip
        if rng.random() < 0.1:  # comma decimal in revenue
            row["REVENUE_COMPANY"] = f"{revenue:.2f}".replace(".", ",")
        if rng.random() < 0.03:
            row["REVENUE_COMPANY"] = ""
        if rng.random() < 0.02:
            row["MAINOKVED_CODE"], row["MAINOKVED_NAME"] = "", ""
        rows.append(row)
    rows.append(company("u-99998", "99.00", REGIONS[0], 0.5, MAINOKVED_NAME="Неизвестный код"))
    dup = dict(rows[0])
    dup["CITY"] = ""
    rows.append(dup)  # duplicate id with fewer fields
    return rows


def payments(rng: random.Random, bg: list[dict]) -> list[dict]:
    by_okved: dict[str, list[str]] = {}
    for r in bg:
        by_okved.setdefault(r["MAINOKVED_CODE"], []).append(r["SYNTHETIC_U"])
    rows = []
    totals = {"c-001": 31e9, "c-002": 17e9, "c-003": 12e9, "c-004": 26e9, "c-005": 24e9,
              "c-006": 9e9}  # fmt: skip
    for cid, okved, role, share in DEMO_LINKS:
        pool = by_okved.get(okved) or [r["SYNTHETIC_U"] for r in bg]
        cp = pool[0] if (cid, okved) == ("c-004", "23.51") else rng.choice(pool)
        amount = totals[cid] * share
        payer, benef = (cid, cp) if role == "supplier" else (cp, cid)
        for part in (0.6, 0.4):
            rows.append({"BENEFICIARY": benef, "PAYER": payer,
                         "PAY_AMT": f"{amount * part:.2f}",
                         "PAY_CNT": str(rng.randint(20, 400))})  # fmt: skip
    ids = [r["SYNTHETIC_U"] for r in bg]
    for cid, total in totals.items():
        for _ in range(25):
            cp = rng.choice(ids)
            payer, benef = (cid, cp) if rng.random() < 0.5 else (cp, cid)
            rows.append({"BENEFICIARY": benef, "PAYER": payer,
                         "PAY_AMT": f"{total * rng.uniform(0.001, 0.01):.2f}",
                         "PAY_CNT": str(rng.randint(1, 50))})  # fmt: skip
    for _ in range(3000):
        payer, benef = rng.sample(ids, 2)
        rows.append({"BENEFICIARY": benef, "PAYER": payer,
                     "PAY_AMT": f"{rng.lognormvariate(17, 1.5):.2f}",
                     "PAY_CNT": str(rng.randint(1, 100))})  # fmt: skip
    rows.append({"BENEFICIARY": "c-001", "PAYER": "c-001", "PAY_AMT": "100", "PAY_CNT": "1"})
    rows.append({"BENEFICIARY": "", "PAYER": "u-00001", "PAY_AMT": "abc", "PAY_CNT": ""})
    return rows


def persons(rng: random.Random, bg: list[dict]) -> list[dict]:
    ids = [r["SYNTHETIC_U"] for r in bg]
    rows = []

    def link(fid: str, cid: str) -> None:
        city, region = rng.choice(REGIONS)
        rows.append({"SYNTHETIC_F": fid, "CITY_NAME": city, "RC_NAME": region,
                     "SYNTHETIC_U": cid})  # fmt: skip

    cement = next(r["SYNTHETIC_U"] for r in bg if r["MAINOKVED_CODE"] == "23.51")
    for fid in ("f-0001", "f-0002"):
        link(fid, "c-004")
        link(fid, cement)
    link("f-0003", "c-001")
    link("f-0003", rng.choice(ids))
    for i in range(4, 1200):
        fid = f"f-{i:04d}"
        for cid in rng.sample(ids, rng.choice([1, 1, 1, 2, 3])):
            link(fid, cid)
    for cid in rng.sample(ids, 80):  # a mass director, must be ignored as noise
        link("f-9999", cid)
    return rows


def write(name: str, rows: list[dict], columns: list[str]) -> None:
    with (OUT / name).open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    rng = random.Random(SEED)
    OUT.mkdir(parents=True, exist_ok=True)
    bg = background(rng, 400)
    companies = DEMO + bg
    cement = next(r for r in bg if r["MAINOKVED_CODE"] == "23.51")
    cement["GROUP_ID"] = "g-204"
    write("df_Uid_data_hack.csv", companies, COMPANY_COLUMNS)
    write("df_Fid_Uid_link_hack.csv", persons(rng, bg),
          ["SYNTHETIC_F", "CITY_NAME", "RC_NAME", "SYNTHETIC_U"])  # fmt: skip
    write("df_payments_hack.csv", payments(rng, bg),
          ["BENEFICIARY", "PAYER", "PAY_AMT", "PAY_CNT"])  # fmt: skip
    print(f"Synthetic client data written to {OUT}")


if __name__ == "__main__":
    main()
