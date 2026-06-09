"""
真实 bug 场景 2：日期处理工具
"""
from datetime import datetime


def parse_date(date_str: str) -> datetime:
    """把字符串解析为 datetime 对象，支持 YYYY-MM-DD 格式"""
    # bug：没有处理格式不对的情况，直接崩溃
    return datetime.strptime(date_str, "%Y-%m-%d")


def days_between(date1: str, date2: str) -> int:
    """计算两个日期之间相差的天数"""
    # bug：没有处理 date1 > date2 的情况，返回负数
    d1 = parse_date(date1)
    d2 = parse_date(date2)
    return (d2 - d1).days


def is_weekend(date_str: str) -> bool:
    """判断某天是否是周末"""
    d = parse_date(date_str)
    # bug：weekday() 返回 0-6，周六=5，周日=6，这里写反了
    return d.weekday() < 2
