Implement `round_half_up(value: float, digits: int = 0) -> float`.

Round to `digits` decimal places, with halves always rounded away from zero
(2.5 becomes 3.0, -2.5 becomes -3.0). The result must match what a person expects from
the decimal number as written, for example `round_half_up(2.675, 2)` is `2.68`.
Raise `ValueError` if `digits` is negative.
