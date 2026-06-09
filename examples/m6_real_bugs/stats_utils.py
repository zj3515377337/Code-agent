"""
真实 bug 场景 3：数据统计工具
"""


def mean(numbers: list) -> float:
    """计算平均值"""
    # bug：没有处理空列表，会触发 ZeroDivisionError
    return sum(numbers) / len(numbers)


def median(numbers: list) -> float:
    """计算中位数"""
    # bug：没有处理空列表；排序后索引计算有误
    sorted_nums = sorted(numbers)
    n = len(sorted_nums)
    # bug：偶数个元素时应该取中间两个的平均值，这里只取了一个
    return sorted_nums[n // 2]


def remove_duplicates(items: list) -> list:
    """去除列表中的重复元素，保持原始顺序"""
    # bug：用 set 会丢失顺序
    return list(set(items))
