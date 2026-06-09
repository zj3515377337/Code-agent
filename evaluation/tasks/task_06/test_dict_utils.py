import pytest
from dict_utils import parse_json, get_nested, merge_dicts


def test_parse_json_valid():
    assert parse_json('{"a": 1}') == {"a": 1}

def test_parse_json_invalid():
    with pytest.raises(ValueError, match="无效的 JSON"):
        parse_json("not json")

def test_get_nested_exists():
    d = {"a": {"b": {"c": 42}}}
    assert get_nested(d, "a.b.c") == 42

def test_get_nested_missing():
    d = {"a": {"b": 1}}
    assert get_nested(d, "a.x.y") is None

def test_get_nested_default():
    d = {"a": 1}
    assert get_nested(d, "b.c", default="N/A") == "N/A"

def test_merge_dicts_shallow():
    assert merge_dicts({"a": 1}, {"b": 2}) == {"a": 1, "b": 2}

def test_merge_dicts_deep():
    d1 = {"a": {"x": 1, "y": 2}}
    d2 = {"a": {"y": 3, "z": 4}}
    result = merge_dicts(d1, d2)
    assert result == {"a": {"x": 1, "y": 3, "z": 4}}

def test_merge_dicts_override():
    assert merge_dicts({"a": 1}, {"a": 2}) == {"a": 2}
