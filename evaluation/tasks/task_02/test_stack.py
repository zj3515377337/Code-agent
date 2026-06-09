import pytest
from stack import Stack


def test_push_and_size():
    s = Stack()
    s.push(1)
    s.push(2)
    assert s.size() == 2

def test_pop():
    s = Stack()
    s.push(10)
    s.push(20)
    assert s.pop() == 20
    assert s.size() == 1

def test_pop_empty():
    s = Stack()
    with pytest.raises(IndexError, match="stack is empty"):
        s.pop()

def test_peek():
    s = Stack()
    s.push(1)
    s.push(2)
    assert s.peek() == 2
    assert s.size() == 2

def test_peek_empty():
    s = Stack()
    with pytest.raises(IndexError, match="stack is empty"):
        s.peek()

def test_is_empty_true():
    s = Stack()
    assert s.is_empty() is True

def test_is_empty_false():
    s = Stack()
    s.push(1)
    assert s.is_empty() is False
