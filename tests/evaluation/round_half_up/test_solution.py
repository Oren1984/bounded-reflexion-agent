import pytest
from solution import round_half_up


@pytest.mark.parametrize(
    "value, expected", [(0.5, 1.0), (1.5, 2.0), (2.5, 3.0), (-2.5, -3.0), (2.4, 2.0), (-0.5, -1.0)]
)
def test_halves_round_away_from_zero(value, expected):
    assert round_half_up(value) == expected


@pytest.mark.parametrize(
    "value, digits, expected",
    [(2.675, 2, 2.68), (1.005, 2, 1.01), (-0.125, 2, -0.13), (1234.5678, 2, 1234.57), (0.15, 1, 0.2)],
)
def test_decimal_literals(value, digits, expected):
    assert round_half_up(value, digits) == expected


def test_returns_float():
    assert isinstance(round_half_up(3, 0), float)


def test_negative_digits_rejected():
    with pytest.raises(ValueError):
        round_half_up(12.5, -1)
