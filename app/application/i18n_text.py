from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional


def pick_i18n(d: Optional[dict[str, str]], locale: str) -> str:
    if not d:
        return ""
    return d.get(locale) or d.get("ru") or next(iter(d.values()), "")


def fmt_usd(amount: Decimal) -> str:
    sign = "-" if amount < 0 else ""
    return f"{sign}${abs(amount):.2f}"


def fmt_time(dt: datetime) -> str:
    """`HH:MM UTC` when it is today in UTC, else `DD.MM HH:MM UTC`."""
    utc = dt.astimezone(timezone.utc)
    same_day = utc.date() == datetime.now(timezone.utc).date()
    return utc.strftime("%H:%M UTC" if same_day else "%d.%m %H:%M UTC")


def fmt_date(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%d.%m.%Y")


def country_flag(code: Optional[str]) -> str:
    """ISO 3166-1 alpha-2 code to a flag emoji (regional indicators)."""
    if not code or len(code) != 2 or not code.isascii() or not code.isalpha():
        return ""
    return "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in code.upper())
