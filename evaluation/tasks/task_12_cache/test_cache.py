"""缓存系统测试。"""
import pytest
from lru_cache import LRUCache
from cache_manager import CacheManager


class TestLRUCache:
    def test_put_and_get(self):
        cache = LRUCache(3)
        cache.put("a", 1)
        assert cache.get("a") == 1

    def test_get_nonexistent(self):
        cache = LRUCache(3)
        assert cache.get("nope") is None

    def test_size(self):
        cache = LRUCache(3)
        cache.put("a", 1)
        cache.put("b", 2)
        assert cache.size() == 2

    def test_lru_eviction(self):
        """容量满时应驱逐最久未使用的。"""
        cache = LRUCache(2)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)  # 应驱逐 "a"
        assert cache.get("a") is None
        assert cache.get("b") == 2
        assert cache.get("c") == 3

    def test_get_refreshes_access_order(self):
        """get 应刷新访问顺序，被访问的不应被驱逐。"""
        cache = LRUCache(2)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.get("a")  # 刷新 "a" 的访问顺序
        cache.put("c", 3)  # 应驱逐 "b"（最久未使用），而不是 "a"
        assert cache.get("a") == 1
        assert cache.get("b") is None
        assert cache.get("c") == 3

    def test_delete(self):
        cache = LRUCache(3)
        cache.put("a", 1)
        assert cache.delete("a") is True
        assert cache.get("a") is None
        assert cache.size() == 0

    def test_delete_nonexistent(self):
        cache = LRUCache(3)
        assert cache.delete("nope") is False


class TestCacheManager:
    def test_basic_put_get(self):
        mgr = CacheManager(5)
        mgr.put("key", "value")
        assert mgr.get("key") == "value"

    def test_get_with_loader_hit(self):
        """缓存命中时不调用 loader。"""
        mgr = CacheManager(5)
        mgr.put("key", "cached")
        call_count = [0]
        def loader():
            call_count[0] += 1
            return "loaded"
        result = mgr.get_with_loader("key", loader)
        assert result == "cached"
        assert call_count[0] == 0

    def test_get_with_loader_miss(self):
        """缓存未命中时调用 loader 并回填。"""
        mgr = CacheManager(5)
        call_count = [0]
        def loader():
            call_count[0] += 1
            return "loaded"
        result = mgr.get_with_loader("key", loader)
        assert result == "loaded"
        assert call_count[0] == 1
        # 回填后再次获取不应调用 loader
        result2 = mgr.get_with_loader("key", loader)
        assert result2 == "loaded"
        assert call_count[0] == 1

    def test_invalidate(self):
        mgr = CacheManager(5)
        mgr.put("key", "value")
        assert mgr.invalidate("key") is True
        assert mgr.get("key") is None
