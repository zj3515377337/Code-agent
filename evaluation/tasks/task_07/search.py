def linear_search(arr, target):
    """线性搜索，找到返回索引，未找到返回 -1"""
    # bug：未找到时返回了 0 而不是 -1
    for i, item in enumerate(arr):
        if item == target:
            return i
    return 0


def binary_search(arr, target):
    """二分搜索（要求 arr 已排序），找到返回索引，未找到返回 -1"""
    # bug：循环条件错了，应该是 left <= right
    left, right = 0, len(arr) - 1
    while left < right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1


def find_max(arr):
    """返回列表中的最大值"""
    # bug：空列表时崩溃，应抛 ValueError
    return max(arr)
