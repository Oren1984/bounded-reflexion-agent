import pytest
from solution import moving_average


def test_basic():
    assert moving_average([1, 2, 3, 4], 2) == [1.5, 2.5, 3.5]


def test_window_of_one():
    assert moving_average([3, 5], 1) == [3.0, 5.0]


def test_window_equals_length():
    assert moving_average([2, 4, 6], 3) == [4.0]


def test_rounding_to_two_decimals():
    assert moving_average([1, 2, 2], 3) == [1.67]


def test_window_larger_than_list():
    assert moving_average([1, 2], 3) == []


def test_empty_list():
    assert moving_average([], 2) == []


@pytest.mark.parametrize("window", [0, -2])
def test_invalid_window(window):
    with pytest.raises(ValueError):
        moving_average([1, 2, 3], window)


def test_invalid_window_checked_before_length():
    with pytest.raises(ValueError):
        moving_average([], 0)
