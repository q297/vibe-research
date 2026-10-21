"""Tolerant parsers for noisy CSV values; None means unknown."""

import re

_NULLS = {"", "nan", "none", "null", "na", "n/a", "-", "—", "?", "не определено", "нет данных"}
_TRUE = {"1", "1.0", "true", "t", "y", "yes", "да", "+", "есть", "истина"}
_FALSE = {"0", "0.0", "false", "f", "n", "no", "нет", "-0", "ложь"}
_NUM = re.compile(r"-?\d+(?:[.,]\d+)?")


def clean(value: object) -> str | None:
    if value is None:
        return None
    s = str(value).replace("\xa0", " ").strip()
    return None if s.lower() in _NULLS else s


def parse_flag(value: object) -> bool | None:
    s = clean(value)
    if s is None:
        return None
    low = s.lower()
    if low in _TRUE:
        return True
    if low in _FALSE:
        return False
    try:
        return float(low.replace(",", ".")) > 0
    except ValueError:
        return None


def parse_number(value: object) -> float | None:
    s = clean(value)
    if s is None:
        return None
    s = s.replace(" ", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        m = _NUM.search(s)
        return float(m.group().replace(",", ".")) if m else None


def gradation_midpoint(value: object) -> float | None:
    """'от 100 до 250' -> 175, '1-3 года' -> 2, 'более 5000' -> 6250, 'до 15' -> 7.5"""
    s = clean(value)
    if s is None:
        return None
    low = s.lower().replace(" ", "")
    nums = [float(n.replace(",", ".")) for n in _NUM.findall(low.replace("-", " - "))]
    nums = [abs(n) for n in nums]
    if not nums:
        return None
    if len(nums) >= 2:
        return (nums[0] + nums[1]) / 2
    n = nums[0]
    if low.startswith(("до", "<", "менее", "меньше")):
        return n / 2
    if low.startswith((">", "более", "свыше", "больше", "от")) or low.endswith("+"):
        return n * 1.25
    return n


def parse_client_type(value: object) -> str | None:
    s = clean(value)
    if s is None:
        return None
    low = s.lower()
    if low.startswith(("действ", "active", "текущ", "клиент")) or low == "1":
        return "active"
    if low.startswith(("потенц", "potential", "prospect")) or low == "0":
        return "potential"
    return None
