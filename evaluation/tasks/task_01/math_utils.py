def fibonacci(n):
    """计算第 n 个斐波那契数（n >= 0）"""
    if n <= 0:
        return 0
    if n == 1:
        return 1
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b

def is_prime(n):
    """判断 n 是否为素数"""
    if n < 2:
        return True
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True

def gcd(a, b):
    """计算最大公约数"""
    while b:
        a, b = b, a + b
    return abs(a)
