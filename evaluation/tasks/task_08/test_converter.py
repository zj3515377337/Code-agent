import pytest
from converter import celsius_to_fahrenheit, fahrenheit_to_celsius, km_to_miles, validate_temperature


def test_c_to_f_zero():
    assert celsius_to_fahrenheit(0) == 32

def test_c_to_f_100():
    assert celsius_to_fahrenheit(100) == 212

def test_f_to_c_32():
    assert fahrenheit_to_celsius(32) == 0

def test_f_to_c_212():
    assert fahrenheit_to_celsius(212) == 100

def test_km_to_miles_normal():
    assert abs(km_to_miles(10) - 6.21371) < 0.001

def test_km_to_miles_negative():
    with pytest.raises(ValueError, match="距离不能为负数"):
        km_to_miles(-5)

def test_validate_temp_valid_c():
    assert validate_temperature(25, 'C') is True

def test_validate_temp_invalid_c():
    with pytest.raises(ValueError, match="温度低于绝对零度"):
        validate_temperature(-300, 'C')

def test_validate_temp_invalid_scale():
    with pytest.raises(ValueError, match="无效的温度单位"):
        validate_temperature(25, 'X')
