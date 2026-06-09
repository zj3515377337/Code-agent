"""订单服务模块。"""
from dataclasses import dataclass, field


@dataclass
class OrderItem:
    name: str
    price: float
    quantity: int


@dataclass
class Order:
    order_id: str
    items: list[OrderItem] = field(default_factory=list)
    total: float = 0.0
    status: str = "pending"


class Inventory:
    """简单库存系统。"""
    def __init__(self):
        self._stock = {}  # name -> quantity

    def set_stock(self, name: str, quantity: int):
        self._stock[name] = quantity

    def get_stock(self, name: str) -> int:
        return self._stock.get(name, 0)

    def reduce_stock(self, name: str, quantity: int):
        self._stock[name] = self._stock.get(name, 0) - quantity

    def restore_stock(self, name: str, quantity: int):
        self._stock[name] = self._stock.get(name, 0) + quantity


class OrderService:
    def __init__(self, inventory: Inventory):
        self.inventory = inventory
        self._orders = {}
        self._next_id = 1

    def create_order(self, items: list[tuple[str, float, int]]) -> Order:
        """
        创建订单。
        items: [(name, price, quantity), ...]
        """
        order_id = f"ORD-{self._next_id:04d}"
        self._next_id += 1

        order_items = []
        total = 0.0
        for name, price, quantity in items:
            order_items.append(OrderItem(name=name, price=price, quantity=quantity))
            total += price * quantity

        order = Order(order_id=order_id, items=order_items, total=total)
        self._orders[order_id] = order
        return order

    def cancel_order(self, order_id: str) -> bool:
        """取消订单。"""
        order = self._orders.get(order_id)
        if not order:
            return False
        order.status = "cancelled"
        return True

    def get_order(self, order_id: str) -> Order | None:
        return self._orders.get(order_id)
