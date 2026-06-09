import pytest
from linked_list import LinkedList


def test_append_one():
    ll = LinkedList()
    ll.append(1)
    assert ll.to_list() == [1]
    assert ll.length == 1

def test_append_many():
    ll = LinkedList()
    ll.append(1)
    ll.append(2)
    ll.append(3)
    assert ll.to_list() == [1, 2, 3]
    assert ll.length == 3

def test_prepend():
    ll = LinkedList()
    ll.prepend(1)
    ll.prepend(2)
    assert ll.to_list() == [2, 1]
    assert ll.length == 2

def test_reverse_normal():
    ll = LinkedList()
    for v in [1, 2, 3, 4]:
        ll.append(v)
    ll.reverse()
    assert ll.to_list() == [4, 3, 2, 1]

def test_reverse_empty():
    ll = LinkedList()
    ll.reverse()
    assert ll.to_list() == []

def test_reverse_single():
    ll = LinkedList()
    ll.append(1)
    ll.reverse()
    assert ll.to_list() == [1]
