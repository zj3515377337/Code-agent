import pytest
from str_ops import reverse_string, is_palindrome, count_vowels


def test_reverse_string():
    assert reverse_string("hello") == "olleh"

def test_reverse_empty():
    assert reverse_string("") == ""

def test_is_palindrome_true():
    assert is_palindrome("A man a plan a canal Panama") is True

def test_is_palindrome_false():
    assert is_palindrome("hello") is False

def test_is_palindrome_case():
    assert is_palindrome("Racecar") is True

def test_count_vowels_lower():
    assert count_vowels("hello") == 2

def test_count_vowels_upper():
    assert count_vowels("HELLO") == 2

def test_count_vowels_mixed():
    assert count_vowels("AeIoU") == 5
