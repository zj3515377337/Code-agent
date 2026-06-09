import pytest
from validator import validate_email, validate_password, sanitize_input, mask_phone


def test_email_valid():
    assert validate_email("user@example.com") is True

def test_email_no_dot():
    # @ 后面必须有点号
    assert validate_email("user@example") is False

def test_email_no_at():
    assert validate_email("userexample.com") is False

def test_password_too_short():
    assert validate_password("Ab1") is False

def test_password_no_upper():
    assert validate_password("abcdef12") is False

def test_password_no_lower():
    assert validate_password("ABCDEF12") is False

def test_password_no_digit():
    assert validate_password("Abcdefgh") is False

def test_password_valid():
    assert validate_password("Abcdef12") is True

def test_sanitize_spaces():
    assert sanitize_input("  hello  ") == "hello"

def test_sanitize_html():
    assert sanitize_input("<script>alert(1)</script>hello") == "alert(1)hello"

def test_mask_phone_normal():
    assert mask_phone("13812345678") == "138****5678"

def test_mask_phone_invalid():
    with pytest.raises(ValueError, match="手机号必须为 11 位"):
        mask_phone("123")
