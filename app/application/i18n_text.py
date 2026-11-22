from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def pick_i18n(d: Optional[dict[str, str]], locale: str) -> str:
    if not d:
        return ""
    return d.get(locale) or d.get("ru") or next(iter(d.values()), "")


def fmt_usd(amount: Decimal) -> str:
    sign = "-" if amount < 0 else ""
    return f"{sign}${abs(amount):.2f}"


def _zone(tz: Optional[str]) -> Optional[ZoneInfo]:
    try:
        return ZoneInfo(tz) if tz else None
    except (ZoneInfoNotFoundError, ValueError, OSError):
        return None


def valid_timezone(tz: str) -> bool:
    return _zone(tz) is not None


def fmt_time(dt: datetime, tz: Optional[str]) -> str:
    """`HH:MM` in the user's time zone when it is today there, else `DD.MM HH:MM`. Zone unknown:
    the same in UTC with a ` UTC` suffix."""
    zone = _zone(tz)
    local = dt.astimezone(zone or timezone.utc)
    today = datetime.now(zone or timezone.utc).date()
    text = local.strftime("%H:%M" if local.date() == today else "%d.%m %H:%M")
    return text if zone else f"{text} UTC"


def fmt_date(dt: datetime, tz: Optional[str]) -> str:
    return dt.astimezone(_zone(tz) or timezone.utc).strftime("%d.%m.%Y")


def country_flag(code: Optional[str]) -> str:
    """ISO 3166-1 alpha-2 code to a flag emoji (regional indicators)."""
    if not code or len(code) != 2 or not code.isascii() or not code.isalpha():
        return ""
    return "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in code.upper())
