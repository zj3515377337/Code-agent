"""折扣引擎模块。"""


class DiscountEngine:
    # 满减规则：(门槛金额, 减免金额)
    THRESHOLD_RULES = [
        (200, 20),
        (100, 10),
        (50, 5),
    ]

    def apply_discount(self, total: float, is_vip: bool = False) -> float:
        """
        计算折后价。
        规则：
        1. 先算满减（满足门槛金额就减免）
        2. VIP 额外打 95 折
        3. 满减和 VIP 折扣叠加
        """
        discounted = total

        # 满减：找到第一个满足条件的规则
        for threshold, reduction in self.THRESHOLD_RULES:
            if discounted > threshold:
                discounted -= reduction
                break

        # VIP 折扣
        if is_vip:
            discounted *= 0.95

        return round(discounted, 2)
