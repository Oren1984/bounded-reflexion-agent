import pytest
from solution import merge_intervals


def test_empty():
    assert merge_intervals([]) == []


def test_overlapping_unsorted():
    assert merge_intervals([(8, 10), (1, 3), (2, 6)]) == [(1, 6), (8, 10)]


def test_touching_intervals_merge():
    assert merge_intervals([(1, 2), (2, 3)]) == [(1, 3)]


def test_adjacent_but_not_touching_stay_separate():
    assert merge_intervals([(1, 2), (3, 4)]) == [(1, 2), (3, 4)]


def test_nested():
    assert merge_intervals([(1, 10), (2, 3), (4, 5)]) == [(1, 10)]


def test_returns_tuples():
    assert all(isinstance(item, tuple) for item in merge_intervals([(1, 2), (2, 5)]))


def test_input_not_modified():
    data = [(5, 6), (1, 2)]
    merge_intervals(data)
    assert data == [(5, 6), (1, 2)]


def test_invalid_interval():
    with pytest.raises(ValueError):
        merge_intervals([(3, 1)])
