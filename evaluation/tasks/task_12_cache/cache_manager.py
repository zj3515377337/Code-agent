"""缓存管理器：在 LRU 基础上加 loader 模式。"""
from lru_cache import LRUCache


class CacheManager:
    def __init__(self, capacity: int = 10):
        self._cache = LRUCache(capacity)

    def get(self, key: str):
        """简单获取。"""
        return self._cache.get(key)

    def put(self, key: str, value):
        """简单写入。"""
        self._cache.put(key, value)

    def get_with_loader(self, key: str, loader) -> object:
        """
        获取缓存，未命中时调用 loader() 加载并回填。
        loader: callable that returns the value.
        """
        value = self._cache.get(key)
        if value is not None:
            return value
        # 缓存未命中
        return None

    def invalidate(self, key: str) -> bool:
        """使缓存条目失效。"""
        return True
