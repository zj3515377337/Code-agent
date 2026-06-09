"""事件定义模块。"""


class Event:
    def __init__(self, event_type: str, data: dict = None):
        self.event_type = event_type
        self.data = data or {}
        self._propagated = True

    def stop_propagation(self):
        """阻止事件继续传播。"""
        self._propagated = False

    @property
    def propagated(self) -> bool:
        return self._propagated
