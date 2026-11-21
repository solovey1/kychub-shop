from decimal import Decimal
from typing import Optional


def pick_i18n(d: Optional[dict[str, str]], locale: str) -> str:
    if not d:
        return ""
    return d.get(locale) or d.get("ru") or next(iter(d.values()), "")


def fmt_usd(amount: Decimal) -> str:
    sign = "-" if amount < 0 else ""
    return f"{sign}${abs(amount):.2f}"


def country_flag(code: Optional[str]) -> str:
    """ISO 3166-1 alpha-2 code to a flag emoji (regional indicators)."""
    if not code or len(code) != 2 or not code.isascii() or not code.isalpha():
        return ""
    return "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in code.upper())
