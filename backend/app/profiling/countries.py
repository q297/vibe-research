"""FTS country names -> ISO 3166-1 alpha-2."""

import re

# fmt: off
_RU_TO_ISO = {
    "китай": "CN", "кнр": "CN", "китайская народная республика": "CN", "гонконг": "HK",
    "турция": "TR", "индия": "IN", "казахстан": "KZ", "беларусь": "BY", "белоруссия": "BY",
    "республика беларусь": "BY", "узбекистан": "UZ", "киргизия": "KG", "кыргызстан": "KG",
    "армения": "AM", "азербайджан": "AZ", "грузия": "GE", "таджикистан": "TJ",
    "туркменистан": "TM", "монголия": "MN", "оаэ": "AE", "объединенные арабские эмираты": "AE",
    "саудовская аравия": "SA", "иран": "IR", "египет": "EG", "израиль": "IL", "катар": "QA",
    "вьетнам": "VN", "таиланд": "TH", "индонезия": "ID", "малайзия": "MY", "сингапур": "SG",
    "япония": "JP", "южная корея": "KR", "корея": "KR", "республика корея": "KR",
    "кндр": "KP", "тайвань": "TW", "бразилия": "BR", "аргентина": "AR", "мексика": "MX",
    "чили": "CL", "перу": "PE", "сша": "US", "соединенные штаты": "US", "канада": "CA",
    "германия": "DE", "франция": "FR", "италия": "IT", "испания": "ES", "нидерланды": "NL",
    "бельгия": "BE", "швейцария": "CH", "австрия": "AT", "польша": "PL", "чехия": "CZ",
    "финляндия": "FI", "швеция": "SE", "норвегия": "NO", "дания": "DK", "великобритания": "GB",
    "соединенное королевство": "GB", "ирландия": "IE", "сербия": "RS", "венгрия": "HU",
    "словакия": "SK", "словения": "SI", "греция": "GR", "кипр": "CY", "латвия": "LV",
    "литва": "LT", "эстония": "EE", "молдова": "MD", "молдавия": "MD", "украина": "UA",
    "румыния": "RO", "болгария": "BG", "португалия": "PT", "люксембург": "LU",
    "юар": "ZA", "южно-африканская республика": "ZA", "нигерия": "NG", "алжир": "DZ",
    "марокко": "MA", "тунис": "TN", "эфиопия": "ET", "кения": "KE", "пакистан": "PK",
    "бангладеш": "BD", "шри-ланка": "LK", "австралия": "AU", "новая зеландия": "NZ",
    "абхазия": "AB", "россия": "RU", "российская федерация": "RU",
}
# fmt: on

_SPLIT = re.compile(r"[;,/|]+")

_ISO_NAMES: dict[str, str] = {}
for _name, _iso in _RU_TO_ISO.items():
    _ISO_NAMES.setdefault(_iso, _name[:1].upper() + _name[1:])
_ISO_NAMES |= {"AE": "ОАЭ", "US": "США", "KR": "Южная Корея", "ZA": "ЮАР", "KP": "КНДР"}


def iso_name(code: str) -> str:
    return _ISO_NAMES.get(code, code)


def _norm(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower().replace("ё", "е"))


def parse_countries(raw: str | None) -> tuple[list[str], list[str]]:
    if raw is None:
        return [], []
    text = str(raw).strip()
    if not text or text.lower() in {"nan", "none", "null", "-", "нет"}:
        return [], []
    iso: list[str] = []
    names: list[str] = []
    for part in _SPLIT.split(text):
        part = part.strip()
        if not part:
            continue
        names.append(part)
        code = _RU_TO_ISO.get(_norm(part))
        if code is None and len(part) == 2 and part.isalpha():
            code = part.upper()  # already ISO
        if code and code != "RU" and code not in iso:
            iso.append(code)
    return iso, names
