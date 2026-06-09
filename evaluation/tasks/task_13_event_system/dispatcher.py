"""事件分发器模块。"""
from event import Event


class EventDispatcher:
    def __init__(self):
        self._handlers = {}  # event_type -> [handler_func]

    def on(self, event_type: str, handler):
        """注册事件处理器。"""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def dispatch(self, event: Event) -> list:
        """
        分发事件给所有注册的处理器。
        返回所有处理器的返回值列表。
        """
        results = []
        handlers = self._handlers.get(event.event_type, [])
        for handler in handlers:
            if not event.propagated:
                break
            result = handler(event)
            results.append(result)
        return results
