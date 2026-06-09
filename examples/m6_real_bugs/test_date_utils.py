import pytest
from date_utils import parse_date, days_between, is_weekend


def test_parse_date_normal():
    d = parse_date("2024-01-15")
    assert d.year == 2024
    assert d.month == 1
    assert d.day == 15


def test_parse_date_invalid():
    with pytest.raises(ValueError, match="日期格式错误"):
        parse_date("2024/01/15")


def test_days_between_forward():
    assert days_between("2024-01-01", "2024-01-10") == 9


def test_days_between_backward():
    # date1 > date2 时应该返回正数（绝对值）
    assert days_between("2024-01-10", "2024-01-01") == 9


def test_is_weekend_saturday():
    assert is_weekend("2024-01-06") is True   # 2024-01-06 是周六


def test_is_weekend_sunday():
    assert is_weekend("2024-01-07") is True   # 2024-01-07 是周日


def test_is_weekend_monday():
    assert is_weekend("2024-01-08") is False  # 2024-01-08 是周一
