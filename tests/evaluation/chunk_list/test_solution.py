import pytest
from solution import chunk_list


def test_even_split():
    assert chunk_list([1, 2, 3, 4], 2) == [[1, 2], [3, 4]]


def test_remainder():
    assert chunk_list([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]


def test_empty():
    assert chunk_list([], 3) == []


def test_size_larger_than_list():
    assert chunk_list([1, 2], 5) == [[1, 2]]


def test_input_not_modified():
    data = [1, 2, 3]
    chunk_list(data, 2)
    assert data == [1, 2, 3]


@pytest.mark.parametrize("size", [0, -1])
def test_size_below_one(size):
    with pytest.raises(ValueError):
        chunk_list([1], size)


@pytest.mark.parametrize("size", ["2", 2.0, None, True])
def test_size_wrong_type(size):
    with pytest.raises(TypeError):
        chunk_list([1, 2], size)
