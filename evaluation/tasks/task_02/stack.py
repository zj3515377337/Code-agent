class Stack:
    def __init__(self):
        self._items = []

    def push(self, item):
        self._items.append(item)

    def pop(self):
        # bug：空栈时应该抛出 IndexError("stack is empty")
        return self._items.pop()

    def peek(self):
        # bug：空栈时应该抛出 IndexError("stack is empty")
        # bug：peek 应该返回栈顶元素而不是栈底
        return self._items[0]

    def size(self):
        return len(self._items)

    def is_empty(self):
        # bug：逻辑反了
        return self.size() > 0
