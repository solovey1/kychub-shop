from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

CENT = Decimal("0.01")


def money(value: str | int | Decimal) -> Decimal:
    """Parse an amount with at most 2 decimal places. Negative values are allowed (ledger sign)."""
    if not isinstance(value, (str, int, Decimal)) or isinstance(value, bool):
        raise TypeError(f"money() accepts str, int or Decimal, got {type(value).__name__}")
    try:
        amount = Decimal(value)
        if not amount.is_finite():
            raise ValueError(f"not a finite amount: {value!r}")
        rounded = amount.quantize(CENT)
    except InvalidOperation as e:
        raise ValueError(f"invalid amount: {value!r}") from e
    if rounded != amount:
        raise ValueError(f"more than 2 decimal places: {value!r}")
    return rounded


def percent_of(amount: Decimal, percent: Decimal) -> Decimal:
    return (amount * percent / 100).quantize(CENT, rounding=ROUND_HALF_UP)
