def parse_int(s):
    try:
        return int(s)
    except ValueError:
        raise ValueError("无效的数字")


def safe_divide(a, b):
    if b == 0:
        raise ZeroDivisionError("除数不能为零")
    return a / b
