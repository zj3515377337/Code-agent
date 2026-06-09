"""edit.py 工具单元测试。"""
import pytest
import tempfile
from pathlib import Path
from code_agent.tools.edit import (
    tool_write_file, tool_str_replace, tool_replace_function, _check_syntax
)


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


# ── _check_syntax ───────────────────────────────────

class TestCheckSyntax:
    def test_valid_python(self):
        assert _check_syntax("def foo():\n    return 1\n") is None

    def test_invalid_python(self):
        result = _check_syntax("def foo(\n    return 1\n")
        assert result is not None
        assert "语法错误" in result


# ── tool_write_file ─────────────────────────────────

class TestWriteFile:
    def test_write_new_file(self, tmp_dir):
        p = tmp_dir / "new.py"
        result = tool_write_file(str(p), "x = 1\n")
        assert "✅" in result
        assert p.read_text(encoding="utf-8") == "x = 1\n"

    def test_write_creates_parent_dirs(self, tmp_dir):
        p = tmp_dir / "sub" / "dir" / "file.py"
        result = tool_write_file(str(p), "x = 1\n")
        assert "✅" in result
        assert p.exists()

    def test_write_rejects_syntax_error(self, tmp_dir):
        p = tmp_dir / "bad.py"
        result = tool_write_file(str(p), "def foo(\n")
        assert "❌" in result
        assert "语法错误" in result
        assert not p.exists()

    def test_write_non_python_skips_syntax_check(self, tmp_dir):
        p = tmp_dir / "data.txt"
        result = tool_write_file(str(p), "not python code {")
        assert "✅" in result


# ── tool_str_replace ────────────────────────────────

class TestStrReplace:
    def test_replace_success(self, tmp_dir):
        p = tmp_dir / "code.py"
        p.write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
        result = tool_str_replace(
            str(p),
            "return a + b",
            "return a - b"
        )
        assert "✅" in result
        assert "a - b" in p.read_text(encoding="utf-8")

    def test_replace_file_not_found(self, tmp_dir):
        result = tool_str_replace(str(tmp_dir / "nope.py"), "old", "new")
        assert "❌" in result
        assert "不存在" in result

    def test_replace_not_found(self, tmp_dir):
        p = tmp_dir / "code.py"
        p.write_text("x = 1\n", encoding="utf-8")
        result = tool_str_replace(str(p), "x = 2", "x = 3")
        assert "❌" in result
        assert "未找到" in result

    def test_replace_multiple_matches(self, tmp_dir):
        p = tmp_dir / "code.py"
        p.write_text("x = 1\nx = 1\n", encoding="utf-8")
        result = tool_str_replace(str(p), "x = 1", "x = 2")
        assert "❌" in result
        assert "2 处" in result

    def test_replace_rejects_syntax_error(self, tmp_dir):
        p = tmp_dir / "code.py"
        p.write_text("def foo():\n    return 1\n", encoding="utf-8")
        result = tool_str_replace(str(p), "return 1", "return (")
        assert "❌" in result
        assert "语法错误" in result


# ── tool_replace_function ───────────────────────────

class TestReplaceFunction:
    def test_replace_top_level_function(self, tmp_dir):
        p = tmp_dir / "calc.py"
        p.write_text(
            "def add(a, b):\n    return a + b\n\ndef sub(a, b):\n    return a - b\n",
            encoding="utf-8"
        )
        result = tool_replace_function(
            str(p), "add",
            "def add(a, b):\n    return b + a\n"
        )
        assert "✅" in result
        content = p.read_text(encoding="utf-8")
        assert "b + a" in content
        assert "a - b" in content  # sub 不受影响

    def test_replace_method_in_class(self, tmp_dir):
        p = tmp_dir / "cls.py"
        p.write_text(
            "class Calc:\n    def compute(self, x):\n        return x * 2\n",
            encoding="utf-8"
        )
        result = tool_replace_function(
            str(p), "Calc.compute",
            "def compute(self, x):\n    return x * 3\n"
        )
        assert "✅" in result
        assert "x * 3" in p.read_text(encoding="utf-8")

    def test_replace_preserves_indentation(self, tmp_dir):
        p = tmp_dir / "cls.py"
        p.write_text(
            "class Foo:\n    def bar(self):\n        return 1\n",
            encoding="utf-8"
        )
        result = tool_replace_function(
            str(p), "Foo.bar",
            "def bar(self):\n    return 42\n"
        )
        assert "✅" in result
        content = p.read_text(encoding="utf-8")
        # 缩进应保持 4 空格
        assert "        return 42\n" in content

    def test_replace_function_not_found(self, tmp_dir):
        p = tmp_dir / "code.py"
        p.write_text("def foo():\n    pass\n", encoding="utf-8")
        result = tool_replace_function(str(p), "bar", "def bar():\n    pass\n")
        assert "❌" in result
        assert "未找到" in result

    def test_replace_rejects_bad_new_body_syntax(self, tmp_dir):
        p = tmp_dir / "code.py"
        p.write_text("def foo():\n    return 1\n", encoding="utf-8")
        result = tool_replace_function(str(p), "foo", "def foo(\n    return 1\n")
        assert "❌" in result
        assert "语法错误" in result

    def test_replace_file_not_found(self, tmp_dir):
        result = tool_replace_function(str(tmp_dir / "nope.py"), "foo", "def foo(): pass\n")
        assert "❌" in result
