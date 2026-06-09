import pytest
from calculator import add, subtract, multiply, divide


def test_add():
    assert add(1, 2) == 3


def test_subtract():
    assert subtract(5, 3) == 2


def test_multiply():
    assert multiply(3, 4) == 12


def test_divide_normal():
    assert divide(10, 2) == 5.0


def test_divide_by_zero():
    # 期望除以零时抛出 ValueError，而不是崩溃
    with pytest.raises(ValueError, match="除数不能为零"):
        divide(10, 0)
