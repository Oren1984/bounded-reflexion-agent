import pytest
from solution import business_days_between


def test_full_week():
    assert business_days_between("2024-01-01", "2024-01-08") == 5


def test_same_day_is_zero():
    assert business_days_between("2024-01-03", "2024-01-03") == 0


def test_end_is_exclusive():
    assert business_days_between("2024-01-05", "2024-01-06") == 1


def test_weekend_only():
    assert business_days_between("2024-01-06", "2024-01-08") == 0


def test_reversed_range_is_negative():
    assert business_days_between("2024-01-08", "2024-01-01") == -5


def test_across_leap_day():
    assert business_days_between("2024-02-26", "2024-03-04") == 5


def test_full_leap_year():
    assert business_days_between("2024-01-01", "2025-01-01") == 262


@pytest.mark.parametrize("bad", ["2024-13-01", "not a date", "2024-02-30"])
def test_invalid_date(bad):
    with pytest.raises(ValueError):
        business_days_between(bad, "2024-01-01")
