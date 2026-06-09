"""模板引擎测试。"""
import pytest
from context import Context
from tokenizer import tokenize
from renderer import Renderer


class TestContext:
    def test_simple_get(self):
        ctx = Context({"name": "Alice"})
        assert ctx.get("name") == "Alice"

    def test_nested_get(self):
        """
        关键测试：应支持嵌套属性访问。
        "user.name" 应返回 ctx["user"]["name"]。
        """
        ctx = Context({"user": {"name": "Alice", "age": 30}})
        assert ctx.get("user.name") == "Alice"
        assert ctx.get("user.age") == 30

    def test_missing_key_returns_empty(self):
        """
        关键测试：未定义的变量应返回空字符串，不应抛异常。
        """
        ctx = Context({"name": "Alice"})
        assert ctx.get("missing") == ""
        assert ctx.get("deeply.nested.missing") == ""

    def test_scope_push_pop(self):
        ctx = Context({"x": 1})
        ctx.push({"x": 2})
        assert ctx.get("x") == 2
        ctx.pop()
        assert ctx.get("x") == 1


class TestTokenizer:
    def test_plain_text(self):
        tokens = tokenize("hello world")
        assert len(tokens) == 1
        assert tokens[0].type == "text"
        assert tokens[0].value == "hello world"

    def test_variable(self):
        tokens = tokenize("Hello {{ name }}!")
        assert len(tokens) == 3
        assert tokens[1].type == "var"
        assert tokens[1].value == "name"

    def test_for_loop(self):
        tmpl = "{% for item in items %}{{ item }}, {% endfor %}"
        tokens = tokenize(tmpl)
        assert any(t.type == "tag" and "for" in t.value for t in tokens)
        assert any(t.type == "tag" and t.value == "endfor" for t in tokens)


class TestRenderer:
    def test_simple_variable(self):
        r = Renderer()
        result = r.render("Hello {{ name }}!", {"name": "Alice"})
        assert result == "Hello Alice!"

    def test_nested_variable(self):
        """
        关键测试：应支持嵌套变量 {{ user.name }}。
        """
        r = Renderer()
        result = r.render("Hello {{ user.name }}!", {"user": {"name": "Alice"}})
        assert result == "Hello Alice!"

    def test_undefined_variable_renders_empty(self):
        """
        关键测试：未定义变量应渲染为空字符串。
        """
        r = Renderer()
        result = r.render("Hello {{ missing }}!", {"name": "Alice"})
        assert result == "Hello !"

    def test_for_loop(self):
        r = Renderer()
        tmpl = "Items: {% for item in items %}[{{ item }}]{% endfor %}"
        result = r.render(tmpl, {"items": ["a", "b", "c"]})
        assert result == "Items: [a][b][c]"

    def test_for_loop_empty_list(self):
        r = Renderer()
        tmpl = "Items: {% for item in items %}[{{ item }}]{% endfor %}"
        result = r.render(tmpl, {"items": []})
        assert result == "Items: "

    def test_nested_for_loop(self):
        """
        关键测试：嵌套 for 循环应正确渲染。
        """
        r = Renderer()
        tmpl = "{% for group in groups %}[{% for item in group.items %}{{ item }} {% endfor %}]{% endfor %}"
        data = {
            "groups": [
                {"items": ["a", "b"]},
                {"items": ["c", "d"]},
            ]
        }
        result = r.render(tmpl, data)
        assert result == "[a b ][c d ]"

    def test_complex_template(self):
        """综合测试：混合变量、循环、嵌套属性。"""
        r = Renderer()
        tmpl = "Hello {{ user.name }}! Your tasks: {% for t in tasks %}{{ t }}, {% endfor %}Done."
        data = {"user": {"name": "Alice"}, "tasks": ["buy milk", "walk dog"]}
        result = r.render(tmpl, data)
        assert result == "Hello Alice! Your tasks: buy milk, walk dog, Done."
