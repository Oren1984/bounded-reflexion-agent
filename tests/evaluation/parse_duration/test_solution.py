import pytest
from solution import parse_duration


@pytest.mark.parametrize(
    "text, expected",
    [("1h30m", 5400), ("45s", 45), ("2h5s", 7205), ("1h1m1s", 3661), ("  10m ", 600), ("0s", 0)],
)
def test_valid(text, expected):
    assert parse_duration(text) == expected


@pytest.mark.parametrize("text", ["", "   ", "abc", "30", "1m1h", "1h1h", "1.5h", "-1h", "1h 30m"])
def test_invalid(text):
    with pytest.raises(ValueError):
        parse_duration(text)
