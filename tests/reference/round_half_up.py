from decimal import ROUND_HALF_UP, Decimal


def round_half_up(value: float, digits: int = 0) -> float:
    if digits < 0:
        raise ValueError("digits must not be negative")
    quantum = Decimal(1).scaleb(-digits)
    return float(Decimal(str(value)).quantize(quantum, rounding=ROUND_HALF_UP))
