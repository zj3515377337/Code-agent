def celsius_to_fahrenheit(c):
    """摄氏度转华氏度"""
    # bug：公式错了，应该是 c * 9/5 + 32
    return c * 5/9 + 32


def fahrenheit_to_celsius(f):
    """华氏度转摄氏度"""
    # bug：公式错了，应该是 (f - 32) * 5/9
    return (f + 32) * 9/5


def km_to_miles(km):
    """公里转英里"""
    # bug：没有处理负数输入
    return km * 0.621371


def validate_temperature(temp, scale):
    """验证温度是否在物理上合理（绝对零度以上）"""
    # bug：绝对零度判断错了
    if scale == 'C' and temp < -273.15:
        raise ValueError("温度低于绝对零度")
    if scale == 'F' and temp < -459.67:
        raise ValueError("温度低于绝对零度")
    # bug：没有处理无效 scale
    return True
