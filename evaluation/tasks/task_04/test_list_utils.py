import pytest
from list_utils import flatten, chunk, unique_sorted


def test_flatten_simple():
    assert flatten([[1, 2], [3, 4]]) == [1, 2, 3, 4]

def test_flatten_deep():
    assert flatten([[1, [2, 3]], [4]]) == [1, 2, 3, 4]

def test_flatten_empty():
    assert flatten([]) == []

def test_chunk_normal():
    assert chunk([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]

def test_chunk_exact():
    assert chunk([1, 2, 3, 4], 2) == [[1, 2], [3, 4]]

def test_chunk_invalid_size():
    with pytest.raises(ValueError, match="size 必须大于 0"):
        chunk([1, 2, 3], 0)

def test_unique_sorted_normal():
    assert unique_sorted([3, 1, 2, 1, 3]) == [1, 2, 3]

def test_unique_sorted_empty():
    assert unique_sorted([]) == []

def test_unique_sorted_already():
    assert unique_sorted([1, 2, 3]) == [1, 2, 3]
