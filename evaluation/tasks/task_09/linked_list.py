class LinkedList:
    def __init__(self):
        self.head = None
        self.length = 0

    def append(self, value):
        """在末尾添加节点"""
        # bug：没有更新 length
        node = Node(value)
        if self.head is None:
            self.head = node
            return
        current = self.head
        while current.next:
            current = current.next
        current.next = node

    def prepend(self, value):
        """在头部添加节点"""
        # bug：没有更新 length
        node = Node(value)
        node.next = self.head
        self.head = node

    def to_list(self):
        """转为 Python 列表"""
        result = []
        current = self.head
        while current:
            result.append(current.value)
            current = current.next
        return result

    def reverse(self):
        """原地反转链表"""
        # bug：实现错了
        prev = self.head
        current = self.head
        while current:
            current = current.next


class Node:
    def __init__(self, value):
        self.value = value
        self.next = None
