import subprocess
from pathlib import Path


def tool_search_text(pattern: str, path: str = ".", file_glob: str = "*.py",
                     task_hint: str = "") -> str:
    """
    在指定目录下搜索包含 pattern 的代码行。
    使用 ripgrep（rg）搜索，速度比 grep 快 5-10 倍。
    如果没有安装 rg，自动降级为 Python 原生搜索。

    P2 新增（来自论文 Agentic RAG with Reflections）：
    task_hint 不为空时，搜索结果会经过轻量相关性判断，
    不相关时自动换词重搜（最多 2 次）。
    """
    raw_result = _do_search(pattern, path, file_glob)

    # P2：如果提供了任务提示，做相关性判断
    if task_hint and _looks_irrelevant(raw_result, pattern, task_hint):
        print(f"\n[search_reflect] 搜索结果可能不相关，尝试换词重搜...")
        # 尝试用更宽泛的关键词重搜一次
        broader = pattern.split("(")[0].split(".")[0].strip()
        if broader and broader != pattern:
            retry_result = _do_search(broader, path, file_glob)
            if "未找到匹配" not in retry_result:
                return (
                    f"[search_reflect] 原词 `{pattern}` 结果可能不相关，"
                    f"已自动换词 `{broader}` 重搜：\n{retry_result}"
                )

    return raw_result


def _do_search(pattern: str, path: str, file_glob: str) -> str:
    """执行实际搜索，优先 rg，降级 Python。"""
    try:
        result = subprocess.run(
            ["rg", "--line-number", "--glob", file_glob, pattern, path],
            capture_output=True,
            text=True,
            timeout=15,
            encoding="utf-8",
            errors="replace"
        )
        output = result.stdout.strip()
        if not output:
            return f"🔍 未找到匹配：{pattern}"
        lines = output.splitlines()
        if len(lines) > 50:
            output = "\n".join(lines[:50])
            output += f"\n... 共 {len(lines)} 条结果，只显示前 50 条，请精化搜索词"
        return f"🔍 搜索 `{pattern}` 的结果：\n{output}"

    except FileNotFoundError:
        return _python_search(pattern, path, file_glob)
    except subprocess.TimeoutExpired:
        return "❌ 搜索超时，请缩小搜索范围"


def _looks_irrelevant(result: str, pattern: str, task_hint: str) -> bool:
    """
    轻量相关性判断：不调用 LLM，用启发式规则判断。

    判断逻辑：
    - 未找到任何结果 → 可能不相关，值得重搜
    - 结果全在 __pycache__ / test_ 文件里，但任务是修源码 → 可能不相关
    - 结果条数 > 30 且 pattern 很短（< 4 字符）→ 搜索词太宽泛
    """
    if "未找到匹配" in result:
        return True

    lines = result.splitlines()
    # 搜索词太短，结果太多，说明搜索词不够精确
    if len(pattern) < 4 and len(lines) > 30:
        return True

    # 结果全在缓存或测试文件里，但任务提示是修源码
    source_keywords = ["fix", "修复", "bug", "implement", "实现", "add", "添加"]
    task_is_source = any(k in task_hint.lower() for k in source_keywords)
    if task_is_source:
        non_test_lines = [l for l in lines
                          if "__pycache__" not in l and "test_" not in l]
        if not non_test_lines:
            return True

    return False


def _python_search(pattern: str, path: str, file_glob: str) -> str:
    """rg 不可用时的备用搜索，纯 Python 实现。"""
    root = Path(path)
    results = []

    for file in root.rglob(file_glob):
        if any(p in file.parts for p in ["__pycache__", ".venv", ".conda"]):
            continue
        try:
            for i, line in enumerate(
                file.read_text(encoding="utf-8", errors="replace").splitlines(), 1
            ):
                if pattern.lower() in line.lower():
                    results.append(f"{file}:{i}: {line.rstrip()}")
        except Exception:
            continue

    if not results:
        return f"🔍 未找到匹配：{pattern}"

    if len(results) > 50:
        results = results[:50]
        results.append("... 只显示前 50 条，请精化搜索词")

    return f"🔍 搜索 `{pattern}` 的结果：\n" + "\n".join(results)
