def flatten(nested_list):
    """将嵌套列表展平为一维列表"""
    result = []
    for item in nested_list:
        if isinstance(item, list):
            result.extend(flatten(item))
        else:
            result.append(item)
    return result


def chunk(lst, size):
    """将列表分成指定大小的块"""
    # bug：size <= 0 时会死循环
    result = []
    for i in range(0, len(lst), size):
        result.append(lst[i:i + size])
    return result


def unique_sorted(lst):
    """去重并排序"""
    # bug：没有去重，只排序了
    return sorted(lst)
