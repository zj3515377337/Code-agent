def reverse_string(s):
    """反转字符串"""
    # bug：返回了原字符串
    return s


def is_palindrome(s):
    """判断字符串是否回文（忽略大小写和空格）"""
    # bug：没有忽略大小写和空格
    return s == s[::-1]


def count_vowels(s):
    """统计字符串中元音字母的数量（aeiouAEIOU）"""
    # bug：只统计了小写元音
    return sum(1 for c in s if c in 'aeiou')
