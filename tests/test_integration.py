"""
Agent 端到端集成测试。

这些测试会真正调用 LLM API，因此：
- 默认跳过（需要设置 AGENT_INTEGRATION_TEST=1 才运行）
- 需要有效的 API Key
- 每个测试约 30-60 秒

运行方式：
  AGENT_INTEGRATION_TEST=1 python -m pytest tests/test_integration.py -v
"""
import os
import sys
import shutil
import tempfile
import pytest
from pathlib import Path

# 跳过条件：未设置环境变量时跳过
skip_reason = os.environ.get("AGENT_INTEGRATION_TEST") != "1"
pytestmark = pytest.mark.skipif(
    skip_reason,
    reason="集成测试默认跳过，设置 AGENT_INTEGRATION_TEST=1 启用"
)

# 确保 src 在路径中
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def _create_task_dir(task_name: str, source: str, test: str, task_txt: str) -> Path:
    """创建临时任务目录。"""
    task_dir = Path(tempfile.mkdtemp(prefix=f"test_agent_{task_name}_"))
    (task_dir / f"{task_name}.py").write_text(source, encoding="utf-8")
    (task_dir / f"test_{task_name}.py").write_text(test, encoding="utf-8")
    (task_dir / "task.txt").write_text(task_txt, encoding="utf-8")
    return task_dir


def _run_agent(task_dir: Path, task_txt: str) -> dict:
    """运行 Agent 并返回结果。"""
    from code_agent.actor import run as agent_run

    full_task = f"请修复 {task_dir} 目录下的代码 bug，让所有测试通过。\n具体要求：{task_txt}"
    result = agent_run(
        full_task,
        repo_root=str(task_dir),
        use_planner=True,
        use_reflector=True,
        use_reminder=True,
        use_reviewer=True,
    )
    return result


def _run_pytest(task_dir: Path) -> bool:
    """在任务目录运行 pytest，返回是否全部通过。"""
    import subprocess
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-x", "-q", "--tb=line", str(task_dir)],
            capture_output=True, text=True, timeout=60,
            cwd=str(task_dir), encoding="utf-8", errors="replace"
        )
        return result.returncode == 0
    except Exception:
        return False


class TestIntegrationSimple:
    """简单单文件 bug 修复。"""

    def test_fix_missing_null_check(self):
        """修复缺少空值检查的函数。"""
        source = 'def greet(name):\n    return f"Hello, {name.upper()}!"\n'
        test = (
            'import pytest\n'
            'from fix_me import greet\n\n'
            'def test_greet_normal():\n'
            '    assert greet("alice") == "Hello, ALICE!"\n\n'
            'def test_greet_none():\n'
            '    with pytest.raises(TypeError):\n'
            '        greet(None)\n'
        )
        task_txt = "greet 函数对 None 输入没有处理，请修复让测试通过"

        task_dir = _create_task_dir("fix_me", source, test, task_txt)
        try:
            result = _run_agent(task_dir, task_txt)
            passed = _run_pytest(task_dir)
            assert passed, f"Agent 未能修复 bug，状态: {result.get('status')}"
        finally:
            shutil.rmtree(task_dir, ignore_errors=True)

    def test_fix_off_by_one(self):
        """修复 off-by-one 错误。"""
        source = (
            'def get_last_n(lst, n):\n'
            '    """返回列表最后 n 个元素。"""\n'
            '    if n <= 0:\n'
            '        return []\n'
            '    return lst[-n+1:]\n'
        )
        test = (
            'from fix_me import get_last_n\n\n'
            'def test_last_3():\n'
            '    assert get_last_n([1,2,3,4,5], 3) == [3,4,5]\n\n'
            'def test_last_1():\n'
            '    assert get_last_n([1,2,3], 1) == [3]\n\n'
            'def test_empty():\n'
            '    assert get_last_n([], 3) == []\n'
        )
        task_txt = "get_last_n 函数返回的元素数量不对，请修复让测试通过"

        task_dir = _create_task_dir("fix_me", source, test, task_txt)
        try:
            result = _run_agent(task_dir, task_txt)
            passed = _run_pytest(task_dir)
            assert passed, f"Agent 未能修复 bug，状态: {result.get('status')}"
        finally:
            shutil.rmtree(task_dir, ignore_errors=True)


class TestIntegrationMultiFile:
    """多文件 bug 修复。"""

    def test_fix_cross_file_import(self):
        """修复跨文件导入问题。"""
        # calculator.py 有一个函数用了错误的导入路径
        source = (
            'def add(a, b):\n'
            '    return a + b\n\n'
            'def multiply(a, b):\n'
            '    return a * b\n'
        )
        # app.py 从错误的模块名导入
        app_source = (
            'from calc import add, multiply\n\n'
            'def calculate_total(items):\n'
            '    total = 0\n'
            '    for item in items:\n'
            '        total = add(total, multiply(item["price"], item["qty"]))\n'
            '    return total\n'
        )
        test = (
            'from app import calculate_total\n\n'
            'def test_total():\n'
            '    items = [{"price": 10, "qty": 2}, {"price": 5, "qty": 3}]\n'
            '    assert calculate_total(items) == 35\n'
        )
        task_txt = "app.py 导入了错误的模块名，请修复让测试通过"

        task_dir = Path(tempfile.mkdtemp(prefix="test_agent_multifile_"))
        (task_dir / "calculator.py").write_text(source, encoding="utf-8")
        (task_dir / "app.py").write_text(app_source, encoding="utf-8")
        (task_dir / "test_app.py").write_text(test, encoding="utf-8")
        (task_dir / "task.txt").write_text(task_txt, encoding="utf-8")
        try:
            result = _run_agent(task_dir, task_txt)
            passed = _run_pytest(task_dir)
            assert passed, f"Agent 未能修复 bug，状态: {result.get('status')}"
        finally:
            shutil.rmtree(task_dir, ignore_errors=True)
