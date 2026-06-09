"""事件系统集成测试。"""
import pytest
from event import Event
from dispatcher import EventDispatcher
from store import EventStore


class TestEventDispatcher:
    def test_single_handler(self):
        d = EventDispatcher()
        d.on("click", lambda e: "clicked")
        results = d.dispatch(Event("click"))
        assert results == ["clicked"]

    def test_multiple_handlers_all_called(self):
        """所有处理器都应该被调用。"""
        d = EventDispatcher()
        log = []
        d.on("click", lambda e: log.append("h1"))
        d.on("click", lambda e: log.append("h2"))
        d.on("click", lambda e: log.append("h3"))
        d.dispatch(Event("click"))
        assert log == ["h1", "h2", "h3"]

    def test_handler_exception_does_not_stop_others(self):
        """
        关键测试：某个处理器抛异常时，后续处理器仍应执行。
        异常不应丢失，应被捕获并记录。
        """
        d = EventDispatcher()
        log = []
        d.on("click", lambda e: log.append("h1"))
        d.on("click", lambda e: (_ for _ in ()).throw(RuntimeError("handler error")))
        d.on("click", lambda e: log.append("h3"))
        results = d.dispatch(Event("click"))
        # h1 和 h3 都应执行
        assert "h1" in log
        assert "h3" in log
        # 异常应被捕获并返回为结果
        assert any(isinstance(r, Exception) for r in results)

    def test_stop_propagation(self):
        """stop_propagation 应阻止后续处理器执行。"""
        d = EventDispatcher()
        log = []
        def stopper(e):
            e.stop_propagation()
            log.append("stopper")
        d.on("click", stopper)
        d.on("click", lambda e: log.append("after"))
        d.dispatch(Event("click"))
        assert log == ["stopper"]

    def test_no_handlers_returns_empty(self):
        d = EventDispatcher()
        results = d.dispatch(Event("unknown"))
        assert results == []


class TestEventStore:
    def test_emit_records_history(self):
        d = EventDispatcher()
        d.on("click", lambda e: "ok")
        store = EventStore(d)
        store.emit("click", {"x": 1})
        history = store.get_history()
        assert len(history) == 1
        assert history[0]["type"] == "click"
        assert history[0]["data"] == {"x": 1}

    def test_emit_with_exception_still_records(self):
        """
        关键测试：即使处理器抛异常，事件也应被记录。
        """
        d = EventDispatcher()
        d.on("click", lambda e: (_ for _ in ()).throw(RuntimeError("boom")))
        store = EventStore(d)
        store.emit("click")
        history = store.get_history()
        assert len(history) == 1
        assert history[0]["type"] == "click"

    def test_multiple_events_in_order(self):
        d = EventDispatcher()
        store = EventStore(d)
        store.emit("a")
        store.emit("b")
        store.emit("c")
        types = [h["type"] for h in store.get_history()]
        assert types == ["a", "b", "c"]
