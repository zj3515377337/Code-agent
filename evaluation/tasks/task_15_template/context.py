"""模板上下文：管理变量作用域。"""


class Context:
    def __init__(self, data: dict = None):
        self._stack = [data or {}]

    def push(self, data: dict):
        """压入新的作用域。"""
        self._stack.append(data)

    def pop(self):
        """弹出当前作用域。"""
        if len(self._stack) > 1:
            self._stack.pop()

    def get(self, key: str, default=""):
        """
        获取变量值。
        注意：不支持嵌套属性访问，直接按 key 查找。
        """
        for scope in reversed(self._stack):
            if key in scope:
                return scope[key]
        return default
