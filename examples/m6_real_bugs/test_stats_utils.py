import pytest
from stats_utils import mean, median, remove_duplicates


def test_mean_normal():
    assert mean([1, 2, 3, 4, 5]) == 3.0


def test_mean_empty():
    with pytest.raises(ValueError, match="列表不能为空"):
        mean([])


def test_median_odd():
    assert median([3, 1, 2]) == 2


def test_median_even():
    # 偶数个元素取中间两个的平均值
    assert median([1, 2, 3, 4]) == 2.5


def test_median_empty():
    with pytest.raises(ValueError, match="列表不能为空"):
        median([])


def test_remove_duplicates_normal():
    assert remove_duplicates([1, 2, 3]) == [1, 2, 3]


def test_remove_duplicates_keeps_order():
    # 去重后必须保持原始顺序
    assert remove_duplicates([3, 1, 2, 1, 3]) == [3, 1, 2]


def test_remove_duplicates_empty():
    assert remove_duplicates([]) == []
