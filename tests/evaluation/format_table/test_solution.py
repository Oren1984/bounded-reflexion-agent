import pytest
from solution import format_table


def test_basic_table():
    rows = [["name", "qty"], ["apple", "3"], ["kiwi", "12"]]
    assert format_table(rows) == "name  | qty\n------+----\napple | 3\nkiwi  | 12"


def test_no_trailing_whitespace_on_any_line():
    rows = [["a", "long header"], ["value", "x"]]
    assert all(line == line.rstrip() for line in format_table(rows).split("\n"))


def test_no_trailing_newline():
    assert not format_table([["a"], ["b"]]).endswith("\n")


def test_header_only():
    assert format_table([["id", "name"]]) == "id | name\n---+-----"


def test_empty_input():
    assert format_table([]) == ""


def test_ragged_rows_rejected():
    with pytest.raises(ValueError):
        format_table([["a", "b"], ["only one"]])
