import pytest
from search import linear_search, binary_search, find_max


def test_linear_search_found():
    assert linear_search([10, 20, 30, 40], 30) == 2

def test_linear_search_not_found():
    assert linear_search([10, 20, 30], 99) == -1

def test_linear_search_empty():
    assert linear_search([], 1) == -1

def test_binary_search_found():
    assert binary_search([1, 3, 5, 7, 9], 7) == 3

def test_binary_search_not_found():
    assert binary_search([1, 3, 5, 7, 9], 4) == -1

def test_binary_search_first():
    assert binary_search([1, 3, 5, 7, 9], 1) == 0

def test_binary_search_last():
    assert binary_search([1, 3, 5, 7, 9], 9) == 4

def test_find_max_normal():
    assert find_max([3, 1, 4, 1, 5]) == 5

def test_find_max_empty():
    with pytest.raises(ValueError, match="列表不能为空"):
        find_max([])

def test_find_max_negative():
    assert find_max([-5, -1, -3]) == -1
