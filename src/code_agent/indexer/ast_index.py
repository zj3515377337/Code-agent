import ast
import os
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class FunctionInfo:
    """一个函数或方法的基本信息。"""
    name: str
    file: str
    line_start: int
    line_end: int
    class_name: str | None = None
    args: list[str] = field(default_factory=list)

    def signature(self) -> str:
        args_str = ", ".join(self.args)
        prefix = f"{self.class_name}." if self.class_name else ""
        return f"{prefix}{self.name}({args_str})"

    def location(self) -> str:
        return f"{self.file}:{self.line_start}"


@dataclass
class ClassInfo:
    """一个类的基本信息。"""
    name: str
    file: str
    line_start: int
    line_end: int
    methods: list[str] = field(default_factory=list)

    def location(self) -> str:
        return f"{self.file}:{self.line_start}"


class ASTIndex:
    """
    Python 项目的 AST 符号索引。

    P3 升级（来自论文 Symbolic-Semantic Indexing）：
    在原有符号层（类名/函数名/行号）之上，新增语义层：
    - 每个文件生成 ≤100 字的"意图摘要"
    - 新增 search_intent() 查询 API，支持自然语言描述找文件
    """

    SKIP_DIRS = {".venv", "__pycache__", ".conda", "node_modules", ".git"}

    def __init__(self):
        self._functions: dict[str, list[FunctionInfo]] = {}
        self._classes: dict[str, list[ClassInfo]] = {}
        self._files_indexed: list[str] = []
        # P3 新增：文件意图摘要 filepath -> summary
        self._file_summaries: dict[str, str] = {}

    def index_repo(self, root: str = ".") -> int:
        """扫描目录下所有 .py 文件，建立符号索引。"""
        root_path = Path(root)
        count = 0
        for py_file in root_path.rglob("*.py"):
            if any(p in py_file.parts for p in self.SKIP_DIRS):
                continue
            if self._index_file(str(py_file)):
                count += 1
        return count

    def _index_file(self, filepath: str) -> bool:
        """解析单个文件，提取所有类和函数信息，并生成意图摘要。"""
        try:
            source = Path(filepath).read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source, filename=filepath)
        except SyntaxError:
            return False
        except Exception:
            return False

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = [
                    n.name for n in ast.walk(node)
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                ]
                self._classes.setdefault(node.name, []).append(ClassInfo(
                    name=node.name, file=filepath,
                    line_start=node.lineno,
                    line_end=getattr(node, "end_lineno", node.lineno),
                    methods=methods
                ))
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                class_name = self._find_parent_class(tree, node)
                args = [a.arg for a in node.args.args]
                self._functions.setdefault(node.name, []).append(FunctionInfo(
                    name=node.name, file=filepath,
                    line_start=node.lineno,
                    line_end=getattr(node, "end_lineno", node.lineno),
                    class_name=class_name, args=args
                ))

        # P3：生成文件意图摘要（不调用 LLM，用启发式规则）
        self._file_summaries[filepath] = self._make_summary(filepath, source, tree)
        self._files_indexed.append(filepath)
        return True

    def _make_summary(self, filepath: str, source: str, tree: ast.AST) -> str:
        """
        用启发式规则生成文件意图摘要，不调用 LLM，零成本。

        规则：
        1. 优先取文件顶部的 docstring
        2. 没有 docstring 则取所有顶层函数名拼成描述
        3. 最多 100 字
        """
        # 尝试取模块级 docstring
        docstring = ast.get_docstring(tree)
        if docstring:
            summary = docstring.replace("\n", " ").strip()
            return summary[:100]

        # 没有 docstring，用函数名和类名拼描述
        top_funcs = [
            node.name for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        top_classes = [
            node.name for node in ast.walk(tree)
            if isinstance(node, ast.ClassDef)
        ]
        filename = Path(filepath).stem

        parts = []
        if top_classes:
            parts.append(f"类：{', '.join(top_classes[:3])}")
        if top_funcs:
            parts.append(f"函数：{', '.join(top_funcs[:5])}")

        summary = f"{filename} | " + "；".join(parts) if parts else filename
        return summary[:100]

    def _find_parent_class(self, tree: ast.AST, func_node: ast.AST) -> str | None:
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for child in ast.walk(node):
                    if child is func_node:
                        return node.name
        return None

    # ── 原有查询 API ──────────────────────────────────

    def search_class(self, class_name: str) -> str:
        results = self._classes.get(class_name, [])
        if not results:
            return f"❌ 未找到类：{class_name}"
        lines = []
        for cls in results:
            lines.append(f"📦 class {cls.name}  [{cls.location()}]")
            lines.append(f"   方法：{', '.join(cls.methods) if cls.methods else '（无方法）'}")
        return "\n".join(lines)

    def search_method(self, method_name: str) -> str:
        results = self._functions.get(method_name, [])
        if not results:
            return f"❌ 未找到函数：{method_name}"
        lines = []
        for func in results:
            lines.append(f"🔧 {func.signature()}  [{func.location()}]")
        return "\n".join(lines)

    def search_method_in_class(self, method_name: str, class_name: str) -> str:
        results = [
            f for f in self._functions.get(method_name, [])
            if f.class_name == class_name
        ]
        if not results:
            return f"❌ 在类 {class_name} 中未找到方法：{method_name}"
        return "\n".join(f"🔧 {f.signature()}  [{f.location()}]" for f in results)

    def search_method_in_file(self, method_name: str, filepath: str) -> str:
        # 统一路径分隔符，兼容 / 和 \
        fp = filepath.replace("\\", "/")
        results = [
            f for f in self._functions.get(method_name, [])
            if fp in f.file.replace("\\", "/")
        ]
        if not results:
            return f"❌ 在文件 {filepath} 中未找到函数：{method_name}"
        return "\n".join(f"🔧 {f.signature()}  [{f.location()}]" for f in results)

    def get_file_symbols(self, filepath: str) -> str:
        fp = filepath.replace("\\", "/")
        classes = [c for clist in self._classes.values() for c in clist if fp in c.file.replace("\\", "/")]
        funcs   = [f for flist in self._functions.values() for f in flist if fp in f.file.replace("\\", "/")]
        if not classes and not funcs:
            return f"❌ 文件 {filepath} 中没有找到任何符号（或文件未被索引）"
        lines = [f"📄 {filepath} 的符号概览："]
        for cls in sorted(classes, key=lambda x: x.line_start):
            lines.append(f"  📦 class {cls.name} (第 {cls.line_start} 行)")
        for func in sorted(funcs, key=lambda x: x.line_start):
            prefix = "    └─" if func.class_name else "  "
            lines.append(f"{prefix}🔧 {func.signature()} (第 {func.line_start} 行)")
        return "\n".join(lines)

    # ── P3 新增：语义层查询 API ───────────────────────

    def search_intent(self, query: str) -> str:
        """
        用自然语言描述查找相关文件。
        比如 search_intent("除法运算") 能找到 calculator.py。

        实现：关键词匹配文件意图摘要，按匹配度排序。
        不调用 LLM，零成本，毫秒级响应。
        """
        if not self._file_summaries:
            return "❌ 索引为空，请先调用 index_repo()"

        query_words = set(query.lower().split())
        scored: list[tuple[float, str, str]] = []

        for filepath, summary in self._file_summaries.items():
            summary_lower = summary.lower()
            # 计算关键词命中数
            hits = sum(1 for w in query_words if w in summary_lower)
            # 文件名也参与匹配
            fname = Path(filepath).stem.lower()
            fname_hits = sum(1 for w in query_words if w in fname)
            score = hits + fname_hits * 2  # 文件名命中权重更高
            if score > 0:
                scored.append((score, filepath, summary))

        if not scored:
            return f"🔍 未找到与 `{query}` 相关的文件\n提示：尝试用更简短的关键词，如函数名或模块名"

        scored.sort(key=lambda x: -x[0])
        lines = [f"🔍 与 `{query}` 相关的文件："]
        for score, filepath, summary in scored[:5]:
            lines.append(f"  📄 {filepath}")
            lines.append(f"     摘要：{summary}")
        return "\n".join(lines)

    def list_file_summaries(self) -> str:
        """列出所有已索引文件的意图摘要，帮助 Agent 快速了解项目全貌。"""
        if not self._file_summaries:
            return "❌ 索引为空"
        lines = ["📚 项目文件意图摘要："]
        for filepath, summary in sorted(self._file_summaries.items()):
            fname = Path(filepath).name
            lines.append(f"  📄 {fname}: {summary}")
        return "\n".join(lines)

    def stats(self) -> str:
        summary_count = len(self._file_summaries)
        return (
            f"📊 索引统计：{len(self._files_indexed)} 个文件，"
            f"{sum(len(v) for v in self._classes.values())} 个类，"
            f"{sum(len(v) for v in self._functions.values())} 个函数，"
            f"{summary_count} 个文件已生成意图摘要"
        )

