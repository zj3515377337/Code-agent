"""购物车模块。"""


class Cart:
    def __init__(self):
        self.items = []  # list of (name, price, quantity)

    def add_item(self, name: str, price: float, quantity: int = 1):
        """添加商品到购物车。"""
        self.items.append((name, price, quantity))

    def remove_item(self, name: str):
        """移除指定商品。"""
        self.items = [(n, p, q) for n, p, q in self.items if n != name]

    def get_item_count(self) -> int:
        """获取商品种类数。"""
        return len(self.items)

    def get_total_quantity(self) -> int:
        """获取商品总数量。"""
        return sum(q for _, _, q in self.items)

    def total(self) -> float:
        """计算总价。"""
        return sum(p * q for _, p, q in self.items)

    def clear(self):
        self.items = []
