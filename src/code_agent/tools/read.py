from pathlib import Path

# 每次最多显示的行数，来自论文资料 11（SWE-agent 实证：100 行最佳）
WINDOW_SIZE = 100


def tool_read_file(path: str, offset: int = 0) -> str:
    """
    读取文件内容，每次最多返回 WINDOW_SIZE 行。
    offset 是从第几行开始读（0 表示从头开始）。
    """
    p = Path(path)
    if not p.exists():
        return f"❌ 文件不存在：{path}"
    if not p.is_file():
        return f"❌ 路径不是文件：{path}"

    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    total = len(lines)
    start = offset
    end = min(offset + WINDOW_SIZE, total)
    chunk = lines[start:end]

    # 拼接带行号的输出，方便 LLM 定位
    numbered = "\n".join(f"{start + i + 1:4d} | {line}" for i, line in enumerate(chunk))
    header = f"📄 {path}  （第 {start + 1}-{end} 行，共 {total} 行）\n"

    hint = ""
    if end < total:
        hint = f"\n... 还有 {total - end} 行未显示，可用 offset={end} 继续读取"

    return header + numbered + hint


def tool_list_dir(path: str = ".") -> str:
    """列出目录下的文件和子目录，帮助 Agent 了解项目结构。"""
    p = Path(path)
    if not p.exists():
        return f"❌ 目录不存在：{path}"
    if not p.is_dir():
        return f"❌ 路径不是目录：{path}"

    items = sorted(p.iterdir(), key=lambda x: (x.is_file(), x.name))
    lines = []
    for item in items:
        prefix = "📁" if item.is_dir() else "📄"
        lines.append(f"{prefix} {item.name}")

    return f"📂 {path}/\n" + "\n".join(lines) if lines else f"📂 {path}/ （空目录）"
