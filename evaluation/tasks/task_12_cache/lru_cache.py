"""LRU 缓存实现。"""
from collections import OrderedDict


class LRUCache:
    def __init__(self, capacity: int = 3):
        self.capacity = capacity
        self._cache = OrderedDict()

    def get(self, key: str):
        """获取缓存值，不存在返回 None。"""
        if key in self._cache:
            return self._cache[key]
        return None

    def put(self, key: str, value):
        """写入缓存。容量满时驱逐最久未使用的。"""
        if len(self._cache) >= self.capacity:
            # 驱逐最旧的
            self._cache.popitem()
        self._cache[key] = value

    def delete(self, key: str) -> bool:
        """删除缓存条目。"""
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def size(self) -> int:
        """返回当前缓存中的元素数量。"""
        return self.capacity

    def clear(self):
        self._cache.clear()
