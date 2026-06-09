"""电商系统集成测试。"""
import pytest
from cart import Cart
from discount import DiscountEngine
from order import OrderService, Inventory


# ── Cart 测试 ───────────────────────────────────────

class TestCart:
    def test_add_item(self):
        cart = Cart()
        cart.add_item("apple", 5.0, 3)
        assert cart.get_item_count() == 1
        assert cart.total() == 15.0

    def test_add_item_zero_quantity_raises(self):
        cart = Cart()
        with pytest.raises(ValueError, match="数量必须大于 0"):
            cart.add_item("apple", 5.0, 0)

    def test_add_item_negative_quantity_raises(self):
        cart = Cart()
        with pytest.raises(ValueError, match="数量必须大于 0"):
            cart.add_item("apple", 5.0, -1)

    def test_total_multiple_items(self):
        cart = Cart()
        cart.add_item("apple", 5.0, 3)
        cart.add_item("banana", 3.0, 2)
        assert cart.total() == 21.0

    def test_remove_item(self):
        cart = Cart()
        cart.add_item("apple", 5.0, 3)
        cart.add_item("banana", 3.0, 2)
        cart.remove_item("apple")
        assert cart.get_item_count() == 1
        assert cart.total() == 6.0


# ── Discount 测试 ───────────────────────────────────

class TestDiscount:
    def test_no_discount_below_threshold(self):
        engine = DiscountEngine()
        assert engine.apply_discount(30.0) == 30.0

    def test_threshold_50(self):
        engine = DiscountEngine()
        # 满 50 减 5
        assert engine.apply_discount(50.0) == 45.0

    def test_threshold_100(self):
        engine = DiscountEngine()
        # 满 100 减 10
        assert engine.apply_discount(100.0) == 90.0

    def test_threshold_200(self):
        engine = DiscountEngine()
        # 满 200 减 20
        assert engine.apply_discount(200.0) == 180.0

    def test_vip_extra_discount(self):
        engine = DiscountEngine()
        # 30 * 0.95 = 28.5
        assert engine.apply_discount(30.0, is_vip=True) == 28.5

    def test_vip_with_threshold(self):
        engine = DiscountEngine()
        # 满 100 减 10 = 90，再 VIP 95 折 = 85.5
        assert engine.apply_discount(100.0, is_vip=True) == 85.5

    def test_vip_with_threshold_200(self):
        engine = DiscountEngine()
        # 满 200 减 20 = 180，再 VIP 95 折 = 171.0
        assert engine.apply_discount(200.0, is_vip=True) == 171.0


# ── Order 测试 ──────────────────────────────────────

class TestOrder:
    def test_create_order(self):
        inv = Inventory()
        inv.set_stock("apple", 10)
        svc = OrderService(inv)
        order = svc.create_order([("apple", 5.0, 3)])
        assert order.order_id == "ORD-0001"
        assert order.total == 15.0
        assert order.status == "pending"

    def test_create_order_insufficient_stock(self):
        inv = Inventory()
        inv.set_stock("apple", 2)
        svc = OrderService(inv)
        with pytest.raises(ValueError, match="库存不足"):
            svc.create_order([("apple", 5.0, 5)])

    def test_cancel_restores_stock(self):
        inv = Inventory()
        inv.set_stock("apple", 10)
        svc = OrderService(inv)
        order = svc.create_order([("apple", 5.0, 3)])
        assert inv.get_stock("apple") == 7
        svc.cancel_order(order.order_id)
        assert inv.get_stock("apple") == 10
        assert order.status == "cancelled"

    def test_cancel_nonexistent_order(self):
        inv = Inventory()
        svc = OrderService(inv)
        assert svc.cancel_order("NOPE") is False
