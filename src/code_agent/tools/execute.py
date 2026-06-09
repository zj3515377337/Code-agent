import subprocess
import os
import signal
from pathlib import Path

# 危险命令黑名单，这些命令会被直接拒绝
DANGEROUS_PATTERNS = [
    "rm -rf",
    "rmdir /s",
    "del /f",
    "format ",
    "mkfs",
    ":(){:|:&};:",   # fork 炸弹
    "dd if=",
    "shutdown",
    "reboot",
]

# 单次命令最长执行时间（秒）
TIMEOUT = 30

# 输出最多保留的字符数，超出部分写文件，防止撑爆上下文
MAX_OUTPUT_CHARS = 8000


def _is_dangerous(command: str) -> str | None:
    """检查命令是否包含危险模式，返回匹配到的危险词，安全则返回 None。"""
    cmd_lower = command.lower()
    for pattern in DANGEROUS_PATTERNS:
        if pattern.lower() in cmd_lower:
            return pattern
    return None


def tool_execute(command: str, cwd: str = ".") -> str:
    """
    在指定目录下执行 shell 命令，返回输出结果。
    内置危险命令拦截和超时保护。
    """
    # 第一道防线：危险命令拦截
    danger = _is_dangerous(command)
    if danger:
        return (
            f"❌ 命令被拒绝：检测到危险操作 `{danger}`\n"
            f"如果确实需要，请联系用户手动执行。"
        )

    work_dir = Path(cwd).resolve()
    if not work_dir.exists():
        return f"❌ 工作目录不存在：{cwd}"

    try:
        # 用 Popen + 进程组确保超时后能正确杀死子进程
        # Windows: CREATE_NEW_PROCESS_GROUP；Linux: start_new_session
        creation_flags = 0
        if os.name == "nt":
            creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP

        proc = subprocess.Popen(
            command,
            shell=True,
            cwd=str(work_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=creation_flags,
        )

        try:
            stdout, stderr = proc.communicate(timeout=TIMEOUT)
        except subprocess.TimeoutExpired:
            # 杀死整个进程树（Windows 用 taskkill，Linux 用 killpg）
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                    capture_output=True, timeout=10
                )
            else:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            try:
                stdout, stderr = proc.communicate(timeout=5)
            except Exception:
                stdout, stderr = "", ""
            return f"❌ 命令超时（>{TIMEOUT}s）：{command}\n请检查命令是否陷入等待。"

        exit_code = proc.returncode

        stdout = stdout.strip() if stdout else ""
        stderr = stderr.strip() if stderr else ""

        output_parts = []
        if stdout:
            output_parts.append(stdout)
        if stderr:
            output_parts.append(f"[stderr]\n{stderr}")
        full_output = "\n".join(output_parts) if output_parts else "（无输出）"

        if len(full_output) > MAX_OUTPUT_CHARS:
            full_output = full_output[:MAX_OUTPUT_CHARS] + f"\n... 输出过长已截断（共 {len(full_output)} 字符）"

        status = "✅" if exit_code == 0 else "❌"
        return f"{status} 退出码：{exit_code}\n{full_output}"

    except Exception as e:
        return f"❌ 执行出错：{e}"


def tool_run_pytest(path: str = ".", extra_args: str = "-v --tb=short") -> str:
    """
    专门用于运行 pytest 测试，是 tool_execute 的快捷封装。
    在 path 所在目录下执行，确保模块导入正确。
    """
    target = Path(path).resolve()
    if target.is_file():
        cwd = str(target.parent)
        pytest_target = str(target)
    else:
        cwd = str(target)
        pytest_target = str(target)
    command = f"python -m pytest {pytest_target} {extra_args}"
    return tool_execute(command, cwd=cwd)
