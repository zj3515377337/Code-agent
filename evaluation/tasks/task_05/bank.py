class BankAccount:
    def __init__(self, owner, balance=0):
        self.owner = owner
        self.balance = balance

    def deposit(self, amount):
        # bug：没有检查 amount <= 0
        self.balance += amount
        return self.balance

    def withdraw(self, amount):
        # bug：没有检查余额不足
        # bug：没有检查 amount <= 0
        self.balance -= amount
        return self.balance

    def transfer(self, other, amount):
        # bug：转账后没有给 other 加钱
        self.withdraw(amount)
        return self.balance
