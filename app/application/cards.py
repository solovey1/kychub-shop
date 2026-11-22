from dataclasses import dataclass, field
from decimal import Decimal
from html import escape
from typing import Callable

from app.application.i18n_text import country_flag, fmt_usd, pick_i18n
from app.application.models.form_schema import split_files


@dataclass(frozen=True)
class CardField:
    label: dict[str, str]
    value: str
    is_file: bool = False


@dataclass(frozen=True)
class OrderCard:
    """What an executor or a reviewer sees of an order. Never the buyer's identity."""

    order_id: int
    product: dict[str, str]
    country_code: str | None
    country_title: dict[str, str] | None
    paid: Decimal
    earning: Decimal
    deadline_minutes: int
    fields: list[CardField] = field(default_factory=list)


def render_card(tr: Callable[..., str], locale: str, card: OrderCard) -> str:
    place = ""
    if card.country_code:
        title = pick_i18n(card.country_title, locale) or card.country_code
        place = f"{country_flag(card.country_code)} {escape(title)}".strip()
    lines = [
        f"{escape(pick_i18n(f.label, locale))}: "
        + (tr("messages-card-file", n=len(split_files(f.value))) if f.is_file else escape(f.value))
        for f in card.fields
    ]
    return tr(
        "messages-card",
        id=str(card.order_id),
        product=escape(pick_i18n(card.product, locale)),
        place=place or "-",
        earning=fmt_usd(card.earning),
        deadline=fmt_duration(tr, card.deadline_minutes),
        fields="\n".join(lines) or "-",
    )


def fmt_duration(tr: Callable[..., str], minutes: int) -> str:
    hours, rest = divmod(minutes, 60)
    parts = [tr("units-hours", n=hours)] if hours else []
    if rest or not hours:
        parts.append(tr("units-minutes", n=rest))
    return " ".join(parts)
