import pytest
from solution import roman_to_int


@pytest.mark.parametrize(
    "text, expected",
    [("III", 3), ("IV", 4), ("IX", 9), ("LVIII", 58), ("MCMXCIV", 1994), ("MMMCMXCIX", 3999)],
)
def test_valid(text, expected):
    assert roman_to_int(text) == expected


@pytest.mark.parametrize("text", ["", "ABC", "iv", "X I"])
def test_invalid(text):
    with pytest.raises(ValueError):
        roman_to_int(text)
