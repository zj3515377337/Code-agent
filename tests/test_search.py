"""search.py 工具单元测试。"""
import pytest
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

# search.py 顶层导入了 openai（虽然没用到），mock 掉
sys.modules.setdefault("openai", MagicMock())
from code_agent.tools.search import tool_search_text, _looks_irrelevant, _python_search


@pytest.fixture
def sample_project(tmp_path):
    (tmp_path / "main.py").write_text(
        "def hello():\n    print('hello world')\n\ndef goodbye():\n    print('bye')\n",
        encoding="utf-8"
    )
    (tmp_path / "test_main.py").write_text(
        "def test_hello():\n    assert hello() is None\n",
        encoding="utf-8"
    )
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "cached.py").write_text("x = 1\n", encoding="utf-8")
    return tmp_path


# ── _python_search（纯 Python 降级搜索）─────────────

class TestPythonSearch:
    def test_find_match(self, sample_project):
        result = _python_search("hello", str(sample_project), "*.py")
        assert "hello" in result
        assert "main.py" in result

    def test_no_match(self, sample_project):
        result = _python_search("nonexistent_xyz", str(sample_project), "*.py")
        assert "未找到" in result

    def test_skips_pycache(self, sample_project):
        result = _python_search("x = 1", str(sample_project), "*.py")
        # __pycache__ 下的文件应被跳过
        assert "__pycache__" not in result


# ── _looks_irrelevant ───────────────────────────────

class TestLooksIrrelevant:
    def test_no_results_is_irrelevant(self):
        assert _looks_irrelevant("🔍 未找到匹配：foo", "foo", "") is True

    def test_short_pattern_many_results(self):
        long_result = "\n".join(["line"] * 40)
        assert _looks_irrelevant(long_result, "x", "") is True

    def test_normal_result_not_irrelevant(self):
        result = "🔍 搜索 `divide` 的结果：\ncalc.py:13: def divide(a, b):"
        assert _looks_irrelevant(result, "divide", "fix the bug") is False

    def test_only_test_files_when_fixing_source(self):
        result = "test_main.py:1: def test_hello():\ntest_main.py:2: assert True"
        assert _looks_irrelevant(result, "hello", "fix the bug in main.py") is True


# ── tool_search_text 集成 ───────────────────────────

class TestSearchText:
    def test_basic_search(self, sample_project):
        result = tool_search_text("hello", str(sample_project), "*.py")
        assert "hello" in result.lower()

    def test_search_with_task_hint(self, sample_project):
        """task_hint 应该被传递但不影响结果（因为结果是相关的）。"""
        result = tool_search_text(
            "hello", str(sample_project), "*.py",
            task_hint="修复 hello 函数"
        )
        assert "hello" in result.lower()
