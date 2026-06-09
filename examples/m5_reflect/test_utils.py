import pytest
from utils import parse_int, safe_divide


def test_parse_int_normal():
    assert parse_int("42") == 42


def test_parse_int_invalid():
    # 期望非数字字符串时抛出 ValueError，而不是崩溃
    with pytest.raises(ValueError, match="无效的数字"):
        parse_int("abc")


def test_safe_divide_normal():
    assert safe_divide(10, 2) == 5.0


def test_safe_divide_by_zero():
    with pytest.raises(ZeroDivisionError):
        safe_divide(10, 0)
