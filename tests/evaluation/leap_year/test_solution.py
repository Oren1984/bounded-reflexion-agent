import pytest
from solution import is_leap_year


@pytest.mark.parametrize(
    "year, expected",
    [(2000, True), (1900, False), (2024, True), (2023, False), (2100, False), (2400, True)],
)
def test_leap_year(year, expected):
    assert is_leap_year(year) is expected
