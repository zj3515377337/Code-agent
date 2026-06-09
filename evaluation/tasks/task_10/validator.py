import re


def validate_email(email):
    """验证邮箱格式"""
    # bug：正则太简单，没有检查 @ 后面必须有点号
    pattern = r'.+@.+'
    return bool(re.match(pattern, email))


def validate_password(password):
    """验证密码强度：至少 8 位，包含大小写字母和数字"""
    # bug：只检查了长度，没检查大小写和数字
    if len(password) < 8:
        return False
    return True


def sanitize_input(text):
    """清理用户输入：去除首尾空格，移除 HTML 标签"""
    # bug：只去了空格，没移除 HTML 标签
    return text.strip()


def mask_phone(phone):
    """手机号脱敏：13812345678 -> 138****5678"""
    # bug：没有验证手机号长度
    return phone[:3] + "****" + phone[7:]
