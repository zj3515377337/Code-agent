"""
真实 bug 场景 1：字符串处理工具
模拟真实项目中常见的边界条件 bug
"""


def truncate(text: str, max_len: int) -> str:
    """截断字符串，超出部分用 ... 代替"""
    if max_len <= 0:
        raise ValueError("max_len 必须大于 0")
    if len(text) <= max_len:
        return text
    return text[:max_len - 3] + "..."


def count_words(text: str) -> int:
    """统计单词数量"""
    if not text.strip():
        return 0
    return len(text.split())


def capitalize_words(text: str) -> str:
    """每个单词首字母大写"""
    if text is None:
        raise TypeError("text 不能为 None")
    return " ".join(word.capitalize() for word in text.split())
