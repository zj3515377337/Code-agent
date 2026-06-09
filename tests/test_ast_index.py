"""AST 索引单元测试。"""
import pytest
import tempfile
from pathlib import Path
from code_agent.indexer.ast_index import ASTIndex


@pytest.fixture
def sample_project(tmp_path):
    """创建一个临时 Python 项目用于测试。"""
    # 主模块
    (tmp_path / "calculator.py").write_text(
        '"""四则运算计算器。"""\n'
        'class Calculator:\n'
        '    def add(self, a, b):\n'
        '        return a + b\n'
        '    def divide(self, a, b):\n'
        '        return a / b\n'
        '\n'
        'def multiply(x, y):\n'
        '    return x * y\n',
        encoding="utf-8"
    )
    # 工具模块
    (tmp_path / "utils.py").write_text(
        '"""字符串工具函数。"""\n'
        'def reverse_string(s):\n'
        '    return s[::-1]\n'
        '\n'
        'def is_palindrome(s):\n'
        '    return s == s[::-1]\n',
        encoding="utf-8"
    )
    # 无 docstring 的文件
    (tmp_path / "helper.py").write_text(
        'def parse_int(s):\n'
        '    return int(s)\n',
        encoding="utf-8"
    )
    return tmp_path


@pytest.fixture
def index(sample_project):
    idx = ASTIndex()
    idx.index_repo(str(sample_project))
    return idx


# ── 索引构建 ────────────────────────────────────────

class TestIndexing:
    def test_indexes_all_files(self, index):
        assert len(index._files_indexed) == 3

    def test_indexes_classes(self, index):
        results = index._classes.get("Calculator", [])
        assert len(results) == 1
        assert results[0].file.endswith("calculator.py")

    def test_indexes_functions(self, index):
        results = index._functions.get("multiply", [])
        assert len(results) == 1
        assert results[0].args == ["x", "y"]

    def test_indexes_methods(self, index):
        results = index._functions.get("divide", [])
        assert len(results) == 1
        assert results[0].class_name == "Calculator"

    def test_generates_file_summaries(self, index):
        assert len(index._file_summaries) == 3
        # 有 docstring 的文件应使用 docstring 作为摘要
        calc_summary = next(
            v for k, v in index._file_summaries.items()
            if "calculator" in k
        )
        assert "四则运算" in calc_summary

    def test_summary_without_docstring(self, index):
        helper_summary = next(
            v for k, v in index._file_summaries.items()
            if "helper" in k
        )
        # 没有 docstring 时用函数名拼接
        assert "parse_int" in helper_summary


# ── search_class ────────────────────────────────────

class TestSearchClass:
    def test_find_existing_class(self, index):
        result = index.search_class("Calculator")
        assert "class Calculator" in result
        assert "calculator.py" in result

    def test_class_not_found(self, index):
        result = index.search_class("NonExistent")
        assert "❌" in result


# ── search_method ───────────────────────────────────

class TestSearchMethod:
    def test_find_existing_method(self, index):
        result = index.search_method("divide")
        assert "divide" in result
        assert "Calculator" in result

    def test_method_not_found(self, index):
        result = index.search_method("nonexistent")
        assert "❌" in result

    def test_find_top_level_function(self, index):
        result = index.search_method("multiply")
        assert "multiply" in result
        assert "calculator.py" in result


# ── search_method_in_class ──────────────────────────

class TestSearchMethodInClass:
    def test_find_method_in_class(self, index):
        result = index.search_method_in_class("add", "Calculator")
        assert "add" in result
        assert "Calculator" in result

    def test_method_not_in_class(self, index):
        result = index.search_method_in_class("multiply", "Calculator")
        assert "❌" in result


# ── search_method_in_file ───────────────────────────

class TestSearchMethodInFile:
    def test_find_method_in_file(self, index):
        result = index.search_method_in_file("reverse_string", "utils.py")
        assert "reverse_string" in result

    def test_method_not_in_file(self, index):
        result = index.search_method_in_file("divide", "utils.py")
        assert "❌" in result


# ── get_file_symbols ────────────────────────────────

class TestGetFileSymbols:
    def test_symbols_for_calculator(self, index):
        result = index.get_file_symbols("calculator.py")
        assert "class Calculator" in result
        assert "multiply" in result
        assert "divide" in result

    def test_symbols_for_nonexistent(self, index):
        result = index.get_file_symbols("nope.py")
        assert "❌" in result


# ── search_intent ───────────────────────────────────

class TestSearchIntent:
    def test_find_by_intent(self, index):
        result = index.search_intent("四则运算")
        assert "calculator.py" in result

    def test_find_by_docstring_keyword(self, index):
        """有 docstring 的文件用 docstring 做摘要，用 docstring 关键词搜索。"""
        result = index.search_intent("字符串工具")
        assert "utils.py" in result

    def test_intent_not_found(self, index):
        result = index.search_intent("量子计算")
        assert "未找到" in result

    def test_empty_index(self):
        idx = ASTIndex()
        result = index.search_intent("test") if False else idx.search_intent("test")
        assert "索引为空" in result


# ── list_file_summaries ─────────────────────────────

class TestListFileSummaries:
    def test_list_all(self, index):
        result = index.list_file_summaries()
        assert "calculator.py" in result
        assert "utils.py" in result
        assert "helper.py" in result


# ── stats ───────────────────────────────────────────

class TestStats:
    def test_stats_format(self, index):
        s = index.stats()
        assert "3 个文件" in s
        assert "1 个类" in s
        assert "意图摘要" in s


# ── 跳过目录 ────────────────────────────────────────

class TestSkipDirs:
    def test_skips_pycache(self, tmp_path):
        (tmp_path / "__pycache__").mkdir()
        (tmp_path / "__pycache__" / "cached.py").write_text("x = 1\n", encoding="utf-8")
        (tmp_path / "real.py").write_text("y = 2\n", encoding="utf-8")
        idx = ASTIndex()
        count = idx.index_repo(str(tmp_path))
        assert count == 1
        assert any("real.py" in f for f in idx._files_indexed)
