"""结构化日志配置：控制台 + 文件双输出。"""
import logging
import sys
from pathlib import Path


def setup_logging(
    level: int = logging.INFO,
    log_file: str | None = None,
) -> None:
    """
    配置全局日志。

    - 控制台：只输出 WARNING 及以上（不干扰用户看到的 print 输出）
    - 文件：输出 DEBUG 及以上（完整的执行 trace，方便排查问题）
    """
    root = logging.getLogger("code_agent")
    root.setLevel(logging.DEBUG)
    root.handlers.clear()

    # 控制台 handler：WARNING+，简洁格式
    console = logging.StreamHandler(sys.stderr)
    console.setLevel(logging.WARNING)
    console.setFormatter(logging.Formatter(
        "%(levelname)s: %(message)s"
    ))
    root.addHandler(console)

    # 文件 handler：DEBUG+，详细格式
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter(
            "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        ))
        root.addHandler(fh)
