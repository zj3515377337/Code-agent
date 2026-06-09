import pytest
from bank import BankAccount


def test_deposit_normal():
    acc = BankAccount("Alice", 100)
    assert acc.deposit(50) == 150

def test_deposit_negative():
    acc = BankAccount("Alice", 100)
    with pytest.raises(ValueError, match="金额必须大于 0"):
        acc.deposit(-10)

def test_withdraw_normal():
    acc = BankAccount("Alice", 100)
    assert acc.withdraw(30) == 70

def test_withdraw_insufficient():
    acc = BankAccount("Alice", 100)
    with pytest.raises(ValueError, match="余额不足"):
        acc.withdraw(200)

def test_withdraw_negative():
    acc = BankAccount("Alice", 100)
    with pytest.raises(ValueError, match="金额必须大于 0"):
        acc.withdraw(-10)

def test_transfer_normal():
    a = BankAccount("Alice", 100)
    b = BankAccount("Bob", 50)
    a.transfer(b, 30)
    assert a.balance == 70
    assert b.balance == 80

def test_transfer_insufficient():
    a = BankAccount("Alice", 100)
    b = BankAccount("Bob", 50)
    with pytest.raises(ValueError, match="余额不足"):
        a.transfer(b, 200)
