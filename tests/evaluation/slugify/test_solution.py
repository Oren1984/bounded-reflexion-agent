import pytest
from solution import slugify


@pytest.mark.parametrize(
    "title, expected",
    [
        ("Hello,  World!", "hello-world"),
        ("Top 10 Tips", "top-10-tips"),
        ("snake_case_name", "snake-case-name"),
        ("  padded  ", "padded"),
        ("", ""),
        ("---", ""),
    ],
)
def test_basic(title, expected):
    assert slugify(title) == expected


def test_accents_are_transliterated():
    assert slugify("Crème Brûlée") == "creme-brulee"


def test_apostrophes_are_dropped_not_split():
    assert slugify("Don't Stop") == "dont-stop"


def test_non_latin_characters_are_removed():
    assert slugify("日本 go") == "go"
