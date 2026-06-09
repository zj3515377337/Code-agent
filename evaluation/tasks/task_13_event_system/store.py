"""事件存储模块，记录所有已分发的事件。"""
from dispatcher import EventDispatcher
from event import Event


class EventStore:
    def __init__(self, dispatcher: EventDispatcher):
        self.dispatcher = dispatcher
        self._history = []

    def emit(self, event_type: str, data: dict = None) -> list:
        """
        发射事件：创建 Event 对象，分发并记录历史。
        返回分发结果。
        """
        event = Event(event_type, data)
        results = self.dispatcher.dispatch(event)
        self._history.append({
            "type": event_type,
            "data": data,
            "results": results,
        })
        return results

    def get_history(self) -> list:
        return list(self._history)
