import pytest
from math_utils import fibonacci, is_prime, gcd

def test_fibonacci():
    assert fibonacci(0) == 0
    assert fibonacci(1) == 1
    assert fibonacci(10) == 55

def test_is_prime():
    assert is_prime(0) == False
    assert is_prime(1) == False
    assert is_prime(2) == True
    assert is_prime(7) == True
    assert is_prime(4) == False

def test_gcd():
    assert gcd(12, 8) == 4
    assert gcd(100, 75) == 25
    assert gcd(7, 3) == 1
