import json


def parse_json(text):
    """解析 JSON 字符串"""
    # bug：没有处理无效 JSON
    return json.loads(text)


def get_nested(data, path, default=None):
    """用点号路径获取嵌套字典的值，如 get_nested(d, 'a.b.c')"""
    # bug：路径中某个 key 不存在时会崩溃
    keys = path.split('.')
    current = data
    for key in keys:
        current = current[key]
    return current


def merge_dicts(d1, d2):
    """深度合并两个字典，d2 的值覆盖 d1"""
    # bug：只做了浅合并，嵌套字典没有递归合并
    result = d1.copy()
    result.update(d2)
    return result
