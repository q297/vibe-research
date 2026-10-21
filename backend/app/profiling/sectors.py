"""OKVED prefix -> sector -> sensitivity tags (longest prefix wins)."""

from dataclasses import dataclass, field

from app.contracts.clients import ExposureDirection as D
from app.contracts.taxonomy import SensitivityTag as T

R, O, M = D.RISK, D.OPPORTUNITY, D.MIXED


@dataclass(frozen=True)
class SectorRule:
    prefix: str
    sector: str
    tags: dict[T, tuple[float, D]] = field(default_factory=dict)


# fmt: off
_RULES: list[SectorRule] = [
    # A. Agriculture
    SectorRule("01", "Сельское хозяйство", {T.COMMODITIES_AGRI: (0.9, M), T.FX_RATE: (0.5, M),
               T.KEY_RATE: (0.6, R), T.REGULATION: (0.5, M), T.EXPORT_IMPORT: (0.5, M)}),
    SectorRule("02", "Лесное хозяйство", {T.EXPORT_IMPORT: (0.7, M), T.FX_RATE: (0.6, M),
               T.SANCTIONS: (0.5, R), T.LOGISTICS: (0.5, R)}),
    SectorRule("03", "Рыболовство", {T.EXPORT_IMPORT: (0.8, M), T.FX_RATE: (0.7, O),
               T.COMMODITIES_AGRI: (0.6, M), T.REGULATION: (0.5, M)}),
    # B. Mining
    SectorRule("05", "Добыча угля", {T.COMMODITIES_ENERGY: (0.95, O), T.EXPORT_IMPORT: (0.8, M),
               T.FX_RATE: (0.8, O), T.SANCTIONS: (0.7, R), T.LOGISTICS: (0.8, R),
               T.TAXES: (0.5, R)}),
    SectorRule("06", "Добыча нефти и газа", {T.COMMODITIES_ENERGY: (1.0, O), T.FX_RATE: (0.8, O),
               T.SANCTIONS: (0.8, R), T.TAXES: (0.8, R), T.EXPORT_IMPORT: (0.7, M)}),
    SectorRule("07", "Добыча металлических руд", {T.COMMODITIES_METALS: (0.95, O),
               T.FX_RATE: (0.7, O), T.EXPORT_IMPORT: (0.7, M), T.SANCTIONS: (0.6, R),
               T.TAXES: (0.5, R)}),
    SectorRule("07.29.41", "Добыча драгоценных металлов", {T.GOLD: (1.0, O),
               T.COMMODITIES_METALS: (0.7, O), T.FX_RATE: (0.7, O), T.SANCTIONS: (0.6, R),
               T.TAXES: (0.5, R)}),
    SectorRule("08", "Добыча прочих полезных ископаемых", {T.REAL_ESTATE: (0.6, M),
               T.COMMODITIES_METALS: (0.4, M), T.LOGISTICS: (0.5, R)}),
    SectorRule("09", "Нефтесервис", {T.COMMODITIES_ENERGY: (0.8, O), T.SANCTIONS: (0.7, R),
               T.KEY_RATE: (0.5, R)}),
    # C. Manufacturing
    SectorRule("10", "Пищевое производство", {T.COMMODITIES_AGRI: (0.8, R),
               T.CONSUMER_DEMAND: (0.8, O), T.INFLATION: (0.7, M), T.REGULATION: (0.5, R)}),
    SectorRule("11", "Производство напитков", {T.CONSUMER_DEMAND: (0.8, O), T.TAXES: (0.7, R),
               T.REGULATION: (0.7, R), T.INFLATION: (0.5, M)}),
    SectorRule("12", "Табачная промышленность", {T.TAXES: (0.8, R), T.REGULATION: (0.8, R),
               T.CONSUMER_DEMAND: (0.6, O)}),
    SectorRule("13", "Лёгкая промышленность", {T.CONSUMER_DEMAND: (0.7, O),
               T.FX_RATE: (0.6, R), T.EXPORT_IMPORT: (0.5, R)}),
    SectorRule("14", "Лёгкая промышленность", {T.CONSUMER_DEMAND: (0.7, O),
               T.FX_RATE: (0.6, R), T.EXPORT_IMPORT: (0.5, R)}),
    SectorRule("15", "Лёгкая промышленность", {T.CONSUMER_DEMAND: (0.7, O),
               T.FX_RATE: (0.6, R), T.EXPORT_IMPORT: (0.5, R)}),
    SectorRule("16", "Деревообработка", {T.EXPORT_IMPORT: (0.7, M), T.FX_RATE: (0.6, O),
               T.REAL_ESTATE: (0.5, O), T.SANCTIONS: (0.5, R)}),
    SectorRule("17", "Целлюлозно-бумажная промышленность", {T.EXPORT_IMPORT: (0.6, M),
               T.FX_RATE: (0.6, M), T.CONSUMER_DEMAND: (0.4, O)}),
    SectorRule("18", "Полиграфия", {T.CONSUMER_DEMAND: (0.5, O), T.FX_RATE: (0.4, R)}),
    SectorRule("19", "Нефтепереработка", {T.COMMODITIES_ENERGY: (0.95, M), T.TAXES: (0.8, M),
               T.REGULATION: (0.7, M), T.FX_RATE: (0.6, O), T.SANCTIONS: (0.6, R)}),
    SectorRule("20", "Химическая промышленность", {T.COMMODITIES_ENERGY: (0.7, R),
               T.EXPORT_IMPORT: (0.7, M), T.FX_RATE: (0.6, O), T.SANCTIONS: (0.6, R)}),
    SectorRule("21", "Фармацевтика", {T.REGULATION: (0.8, M), T.FX_RATE: (0.7, R),
               T.EXPORT_IMPORT: (0.6, R), T.SANCTIONS: (0.4, R)}),
    SectorRule("22", "Производство резины и пластмасс", {T.COMMODITIES_ENERGY: (0.6, R),
               T.CONSUMER_DEMAND: (0.4, O), T.FX_RATE: (0.4, R)}),
    SectorRule("23", "Производство стройматериалов", {T.REAL_ESTATE: (0.9, O),
               T.KEY_RATE: (0.7, R), T.COMMODITIES_ENERGY: (0.6, R), T.LOGISTICS: (0.5, R)}),
    SectorRule("24", "Металлургия", {T.COMMODITIES_METALS: (0.95, O), T.FX_RATE: (0.8, O),
               T.EXPORT_IMPORT: (0.8, M), T.SANCTIONS: (0.7, R), T.COMMODITIES_ENERGY: (0.5, R),
               T.LOGISTICS: (0.6, R)}),
    SectorRule("24.41", "Производство драгоценных металлов", {T.GOLD: (1.0, O),
               T.COMMODITIES_METALS: (0.7, O), T.FX_RATE: (0.7, O), T.SANCTIONS: (0.6, R)}),
    SectorRule("25", "Производство металлоизделий", {T.COMMODITIES_METALS: (0.8, R),
               T.ECONOMIC_GROWTH: (0.5, O), T.KEY_RATE: (0.5, R)}),
    SectorRule("26", "Электроника", {T.FX_RATE: (0.8, R), T.SANCTIONS: (0.7, R),
               T.EXPORT_IMPORT: (0.7, R), T.REGULATION: (0.5, O)}),
    SectorRule("27", "Электрооборудование", {T.FX_RATE: (0.6, R), T.COMMODITIES_METALS: (0.6, R),
               T.ECONOMIC_GROWTH: (0.5, O), T.SANCTIONS: (0.5, R)}),
    SectorRule("28", "Машиностроение", {T.KEY_RATE: (0.7, R), T.ECONOMIC_GROWTH: (0.6, O),
               T.FX_RATE: (0.6, R), T.SANCTIONS: (0.6, R), T.COMMODITIES_METALS: (0.5, R)}),
    SectorRule("29", "Автопром", {T.KEY_RATE: (0.8, R), T.CONSUMER_DEMAND: (0.8, O),
               T.FX_RATE: (0.7, R), T.SANCTIONS: (0.6, R), T.REGULATION: (0.5, M)}),
    SectorRule("30", "Производство транспортных средств", {T.KEY_RATE: (0.6, R),
               T.SANCTIONS: (0.7, R), T.REGULATION: (0.6, M), T.FX_RATE: (0.5, R)}),
    SectorRule("31", "Производство мебели", {T.CONSUMER_DEMAND: (0.7, O),
               T.REAL_ESTATE: (0.5, O), T.KEY_RATE: (0.4, R)}),
    SectorRule("32", "Прочее производство", {T.CONSUMER_DEMAND: (0.5, O), T.FX_RATE: (0.4, R)}),
    SectorRule("33", "Ремонт и монтаж оборудования", {T.ECONOMIC_GROWTH: (0.5, O),
               T.LABOR_MARKET: (0.5, R)}),
    # D, E. Utilities
    SectorRule("35", "Электроэнергетика", {T.REGULATION: (0.8, M), T.COMMODITIES_ENERGY: (0.7, R),
               T.KEY_RATE: (0.6, R), T.INFLATION: (0.5, M)}),
    SectorRule("36", "Водоснабжение и утилизация", {T.REGULATION: (0.7, M),
               T.INFLATION: (0.5, M), T.KEY_RATE: (0.4, R)}),
    SectorRule("37", "Водоснабжение и утилизация", {T.REGULATION: (0.7, M),
               T.INFLATION: (0.5, M)}),
    SectorRule("38", "Водоснабжение и утилизация", {T.REGULATION: (0.7, M),
               T.COMMODITIES_METALS: (0.4, O)}),
    SectorRule("39", "Водоснабжение и утилизация", {T.REGULATION: (0.7, M)}),
    # F. Construction
    SectorRule("41", "Строительство", {T.KEY_RATE: (0.95, R), T.REAL_ESTATE: (0.95, O),
               T.CREDIT_MARKET: (0.8, R), T.REGULATION: (0.6, M), T.LABOR_MARKET: (0.6, R)}),
    SectorRule("42", "Инфраструктурное строительство", {T.KEY_RATE: (0.7, R),
               T.REGULATION: (0.7, M), T.COMMODITIES_METALS: (0.5, R), T.LABOR_MARKET: (0.6, R),
               T.ECONOMIC_GROWTH: (0.5, O)}),
    SectorRule("43", "Строительство", {T.REAL_ESTATE: (0.8, O), T.KEY_RATE: (0.7, R),
               T.LABOR_MARKET: (0.6, R)}),
    # G. Trade
    SectorRule("45", "Автоторговля", {T.CONSUMER_DEMAND: (0.9, O), T.KEY_RATE: (0.8, R),
               T.FX_RATE: (0.8, R), T.EXPORT_IMPORT: (0.6, R), T.REGULATION: (0.5, M)}),
    SectorRule("46", "Оптовая торговля", {T.CONSUMER_DEMAND: (0.6, O), T.FX_RATE: (0.6, R),
               T.EXPORT_IMPORT: (0.6, M), T.KEY_RATE: (0.5, R), T.LOGISTICS: (0.6, R)}),
    SectorRule("46.2", "Оптовая торговля агросырьём", {T.COMMODITIES_AGRI: (0.9, M),
               T.EXPORT_IMPORT: (0.7, M), T.FX_RATE: (0.6, M), T.LOGISTICS: (0.6, R)}),
    SectorRule("46.3", "Оптовая торговля продуктами", {T.CONSUMER_DEMAND: (0.8, O),
               T.INFLATION: (0.7, M), T.COMMODITIES_AGRI: (0.6, R), T.LOGISTICS: (0.6, R)}),
    SectorRule("46.71", "Оптовая торговля топливом", {T.COMMODITIES_ENERGY: (0.95, M),
               T.TAXES: (0.6, M), T.REGULATION: (0.6, M), T.LOGISTICS: (0.6, R)}),
    SectorRule("46.72", "Оптовая торговля металлами", {T.COMMODITIES_METALS: (0.9, M),
               T.FX_RATE: (0.6, M), T.KEY_RATE: (0.5, R)}),
    SectorRule("47", "Розничная торговля", {T.CONSUMER_DEMAND: (0.95, O), T.INFLATION: (0.85, M),
               T.LABOR_MARKET: (0.6, R), T.FX_RATE: (0.5, R), T.KEY_RATE: (0.4, R)}),
    SectorRule("47.3", "Розничная торговля топливом", {T.COMMODITIES_ENERGY: (0.9, M),
               T.CONSUMER_DEMAND: (0.7, O), T.REGULATION: (0.6, M), T.TAXES: (0.5, M)}),
    # H. Transport
    SectorRule("49", "Наземный транспорт", {T.LOGISTICS: (0.9, M), T.COMMODITIES_ENERGY: (0.7, R),
               T.ECONOMIC_GROWTH: (0.6, O), T.REGULATION: (0.5, M)}),
    SectorRule("49.5", "Трубопроводный транспорт", {T.COMMODITIES_ENERGY: (0.9, O),
               T.REGULATION: (0.8, M), T.SANCTIONS: (0.6, R)}),
    SectorRule("50", "Водный транспорт", {T.LOGISTICS: (0.9, M), T.EXPORT_IMPORT: (0.8, O),
               T.SANCTIONS: (0.7, R), T.FX_RATE: (0.5, O)}),
    SectorRule("51", "Авиаперевозки", {T.COMMODITIES_ENERGY: (0.8, R), T.SANCTIONS: (0.8, R),
               T.FX_RATE: (0.7, R), T.CONSUMER_DEMAND: (0.7, O)}),
    SectorRule("52", "Складская логистика", {T.LOGISTICS: (0.9, O), T.EXPORT_IMPORT: (0.6, O),
               T.ECONOMIC_GROWTH: (0.5, O)}),
    SectorRule("53", "Почтовая и курьерская деятельность", {T.LOGISTICS: (0.8, M),
               T.CONSUMER_DEMAND: (0.7, O), T.LABOR_MARKET: (0.6, R)}),
    # I. Hospitality
    SectorRule("55", "Гостиничный бизнес", {T.CONSUMER_DEMAND: (0.9, O), T.FX_RATE: (0.5, O),
               T.KEY_RATE: (0.5, R)}),
    SectorRule("56", "Общепит", {T.CONSUMER_DEMAND: (0.9, O), T.INFLATION: (0.7, R),
               T.LABOR_MARKET: (0.7, R)}),
    # J. IT and telecom
    SectorRule("58", "Издательская деятельность и ПО", {T.REGULATION: (0.6, M),
               T.LABOR_MARKET: (0.7, R), T.TAXES: (0.6, M)}),
    SectorRule("59", "Медиа", {T.CONSUMER_DEMAND: (0.6, O), T.REGULATION: (0.6, M)}),
    SectorRule("60", "Медиа", {T.CONSUMER_DEMAND: (0.6, O), T.REGULATION: (0.6, M)}),
    SectorRule("61", "Телеком", {T.REGULATION: (0.8, M), T.FX_RATE: (0.6, R),
               T.SANCTIONS: (0.6, R), T.KEY_RATE: (0.5, R)}),
    SectorRule("62", "IT", {T.LABOR_MARKET: (0.8, R), T.TAXES: (0.7, M), T.REGULATION: (0.6, M),
               T.ECONOMIC_GROWTH: (0.5, O)}),
    SectorRule("63", "IT", {T.LABOR_MARKET: (0.7, R), T.REGULATION: (0.6, M),
               T.TAXES: (0.5, M)}),
    # K. Finance
    SectorRule("64", "Финансовые услуги", {T.KEY_RATE: (0.9, M), T.BOND_MARKET: (0.8, M),
               T.CREDIT_MARKET: (0.8, M), T.REGULATION: (0.8, M)}),
    SectorRule("65", "Страхование", {T.KEY_RATE: (0.7, O), T.BOND_MARKET: (0.8, M),
               T.REGULATION: (0.7, M)}),
    SectorRule("66", "Финансовые услуги", {T.KEY_RATE: (0.7, M), T.BOND_MARKET: (0.7, M),
               T.REGULATION: (0.7, M)}),
    # L. Real estate
    SectorRule("68", "Недвижимость", {T.REAL_ESTATE: (0.95, M), T.KEY_RATE: (0.9, R),
               T.CREDIT_MARKET: (0.6, R), T.CONSUMER_DEMAND: (0.5, O)}),
    # M, N. Business services
    SectorRule("69", "Профессиональные услуги", {T.ECONOMIC_GROWTH: (0.6, O),
               T.LABOR_MARKET: (0.6, R), T.REGULATION: (0.4, M)}),
    SectorRule("70", "Управление холдингами и консалтинг", {T.ECONOMIC_GROWTH: (0.6, O),
               T.KEY_RATE: (0.6, R), T.BOND_MARKET: (0.5, M)}),
    SectorRule("71", "Инжиниринг", {T.ECONOMIC_GROWTH: (0.6, O), T.REAL_ESTATE: (0.5, O),
               T.LABOR_MARKET: (0.6, R)}),
    SectorRule("72", "НИОКР", {T.REGULATION: (0.5, M), T.LABOR_MARKET: (0.6, R)}),
    SectorRule("73", "Реклама и маркетинг", {T.CONSUMER_DEMAND: (0.8, O),
               T.ECONOMIC_GROWTH: (0.6, O)}),
    SectorRule("74", "Профессиональные услуги", {T.ECONOMIC_GROWTH: (0.5, O)}),
    SectorRule("75", "Ветеринария", {T.CONSUMER_DEMAND: (0.5, O)}),
    SectorRule("77", "Аренда и лизинг", {T.KEY_RATE: (0.9, R), T.CREDIT_MARKET: (0.7, R),
               T.ECONOMIC_GROWTH: (0.5, O)}),
    SectorRule("78", "Кадровые услуги", {T.LABOR_MARKET: (0.95, M),
               T.ECONOMIC_GROWTH: (0.5, O)}),
    SectorRule("79", "Туризм", {T.CONSUMER_DEMAND: (0.9, O), T.FX_RATE: (0.7, R),
               T.SANCTIONS: (0.5, R)}),
    SectorRule("80", "Охрана и безопасность", {T.LABOR_MARKET: (0.7, R)}),
    SectorRule("81", "Обслуживание зданий", {T.LABOR_MARKET: (0.7, R), T.REAL_ESTATE: (0.5, O)}),
    SectorRule("82", "Административные услуги", {T.LABOR_MARKET: (0.6, R),
               T.ECONOMIC_GROWTH: (0.4, O)}),
    # O-S. Public sector and services
    SectorRule("84", "Государственное управление", {T.REGULATION: (0.8, M), T.TAXES: (0.6, M)}),
    SectorRule("85", "Образование", {T.REGULATION: (0.6, M), T.CONSUMER_DEMAND: (0.5, O)}),
    SectorRule("86", "Здравоохранение", {T.REGULATION: (0.7, M), T.FX_RATE: (0.4, R),
               T.LABOR_MARKET: (0.5, R)}),
    SectorRule("87", "Социальные услуги", {T.REGULATION: (0.6, M)}),
    SectorRule("88", "Социальные услуги", {T.REGULATION: (0.6, M)}),
    SectorRule("90", "Культура и развлечения", {T.CONSUMER_DEMAND: (0.8, O)}),
    SectorRule("91", "Культура и развлечения", {T.CONSUMER_DEMAND: (0.6, O)}),
    SectorRule("92", "Азартные игры", {T.REGULATION: (0.8, M), T.TAXES: (0.7, R),
               T.CONSUMER_DEMAND: (0.7, O)}),
    SectorRule("93", "Спорт и отдых", {T.CONSUMER_DEMAND: (0.8, O)}),
    SectorRule("94", "Общественные организации", {T.REGULATION: (0.5, M)}),
    SectorRule("95", "Бытовые услуги", {T.CONSUMER_DEMAND: (0.7, O)}),
    SectorRule("96", "Бытовые услуги", {T.CONSUMER_DEMAND: (0.7, O)}),
]
# fmt: on

_BY_PREFIX = sorted(_RULES, key=lambda r: len(r.prefix), reverse=True)
UNKNOWN_SECTOR = "Прочее"


def normalize_okved(code: str | None) -> str | None:
    """'24.10.1', '2410', '24,10' and ' 24.10 ' all become dotted form; junk becomes None"""
    if code is None:
        return None
    s = str(code).strip().replace(",", ".").replace(" ", "")
    if not s or s.lower() in {"nan", "none", "null", "-"}:
        return None
    if "." not in s and s.isdigit() and len(s) > 2:
        # '2410' -> '24.10', '46711' -> '46.71.1'
        parts = [s[:2]] + [s[i : i + 2] if i < 4 else s[i:] for i in range(2, len(s), 2)]
        s = ".".join(p for p in parts if p)
    head = s.split(".")[0]
    if not head.isdigit():
        return None
    if len(head) == 1:
        s = "0" + s
    return s


def match_sector(okved_code: str | None) -> SectorRule | None:
    code = normalize_okved(okved_code)
    if not code:
        return None
    # Codes are normalized to dotted form, so a plain prefix test is safe: '46.2' matches '46.21'
    return next((rule for rule in _BY_PREFIX if code.startswith(rule.prefix)), None)


def sector_name(okved_code: str | None) -> str | None:
    rule = match_sector(okved_code)
    return rule.sector if rule else None


def sector_tags(okved_code: str | None) -> dict[T, tuple[float, D]]:
    rule = match_sector(okved_code)
    return dict(rule.tags) if rule else {}
