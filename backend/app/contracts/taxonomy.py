"""Closed dictionary of sensitivity tags (D2), co-owned by roles 2 and 3

Events and client profiles must use the same values, otherwise ranking finds no matches
"""

from enum import StrEnum

TAXONOMY_VERSION = "0.1.0"


class SensitivityTag(StrEnum):
    KEY_RATE = "key_rate"
    FX_RATE = "fx_rate"
    INFLATION = "inflation"
    CONSUMER_DEMAND = "consumer_demand"
    COMMODITIES_ENERGY = "commodities_energy"
    COMMODITIES_METALS = "commodities_metals"
    COMMODITIES_AGRI = "commodities_agri"
    GOLD = "gold"
    CREDIT_MARKET = "credit_market"
    BOND_MARKET = "bond_market"
    EXPORT_IMPORT = "export_import"
    SANCTIONS = "sanctions"
    REGULATION = "regulation"
    TAXES = "taxes"
    LOGISTICS = "logistics"
    LABOR_MARKET = "labor_market"
    OTHER = "other"


TAG_LABELS_RU: dict[SensitivityTag, str] = {
    SensitivityTag.KEY_RATE: "Ключевая ставка",
    SensitivityTag.FX_RATE: "Валютный курс",
    SensitivityTag.INFLATION: "Инфляция",
    SensitivityTag.CONSUMER_DEMAND: "Потребительский спрос",
    SensitivityTag.COMMODITIES_ENERGY: "Энергоносители",
    SensitivityTag.COMMODITIES_METALS: "Металлы",
    SensitivityTag.COMMODITIES_AGRI: "Агросырьё",
    SensitivityTag.GOLD: "Золото",
    SensitivityTag.CREDIT_MARKET: "Кредитный рынок",
    SensitivityTag.BOND_MARKET: "Рынок облигаций",
    SensitivityTag.EXPORT_IMPORT: "ВЭД",
    SensitivityTag.SANCTIONS: "Санкции",
    SensitivityTag.REGULATION: "Регулирование",
    SensitivityTag.TAXES: "Налоги",
    SensitivityTag.LOGISTICS: "Логистика",
    SensitivityTag.LABOR_MARKET: "Рынок труда",
    SensitivityTag.OTHER: "Прочее",
}
