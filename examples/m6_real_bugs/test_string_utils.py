import pytest
from string_utils import truncate, count_words, capitalize_words


def test_truncate_normal():
    assert truncate("hello world", 20) == "hello world"


def test_truncate_long():
    # 截断后总长度应该等于 max_len，不是 max_len + 3
    result = truncate("hello world foo bar", 10)
    assert len(result) == 10
    assert result.endswith("...")


def test_truncate_zero():
    # max_len=0 时应该返回空字符串或抛出 ValueError
    with pytest.raises(ValueError, match="max_len 必须大于 0"):
        truncate("hello", 0)


def test_count_words_normal():
    assert count_words("hello world") == 2


def test_count_words_empty():
    # 空字符串应该返回 0，不是 1
    assert count_words("") == 0


def test_count_words_spaces():
    assert count_words("  hello  world  ") == 2


def test_capitalize_words_normal():
    assert capitalize_words("hello world") == "Hello World"


def test_capitalize_words_none():
    # None 输入应该抛出 TypeError，有明确提示
    with pytest.raises(TypeError, match="text 不能为 None"):
        capitalize_words(None)
