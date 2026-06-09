"""Agent 配置中心：所有可调参数集中管理，支持环境变量覆盖。"""
import os
from dataclasses import dataclass, field


@dataclass
class AgentConfig:
    """
    Agent 全局配置。优先级：构造参数 > 环境变量 > 默认值。

    环境变量前缀：AGENT_
    例如 AGENT_MODEL=deepseek-chat AGENT_MAX_STEPS=30
    """

    # ── LLM 配置 ──────────────────────────────────
    model: str = field(default_factory=lambda: os.environ.get("AGENT_MODEL", "mimo-v2.5-pro"))
    temperature_plan: float = field(default_factory=lambda: float(os.environ.get("AGENT_TEMPERATURE_PLAN", "0.3")))
    temperature_reflect: float = field(default_factory=lambda: float(os.environ.get("AGENT_TEMPERATURE_REFLECT", "0.2")))
    temperature_main: float = field(default_factory=lambda: float(os.environ.get("AGENT_TEMPERATURE_MAIN", "0.7")))

    # ── 执行控制 ──────────────────────────────────
    max_steps: int = field(default_factory=lambda: int(os.environ.get("AGENT_MAX_STEPS", "20")))
    max_retries: int = field(default_factory=lambda: int(os.environ.get("AGENT_MAX_RETRIES", "3")))

    # ── 记忆配置 ──────────────────────────────────
    working_max_rounds: int = field(default_factory=lambda: int(os.environ.get("AGENT_WORKING_ROUNDS", "6")))
    compress_token_threshold: int = field(default_factory=lambda: int(os.environ.get("AGENT_COMPRESS_TOKEN_THRESHOLD", "8000")))
    keep_after_compress_tokens: int = field(default_factory=lambda: int(os.environ.get("AGENT_KEEP_AFTER_COMPRESS_TOKENS", "2000")))
    max_summary_chars: int = field(default_factory=lambda: int(os.environ.get("AGENT_MAX_SUMMARY_CHARS", "500")))

    # ── 工具配置 ──────────────────────────────────
    read_window_size: int = field(default_factory=lambda: int(os.environ.get("AGENT_READ_WINDOW", "100")))
    execute_timeout: int = field(default_factory=lambda: int(os.environ.get("AGENT_EXECUTE_TIMEOUT", "30")))
    execute_max_output: int = field(default_factory=lambda: int(os.environ.get("AGENT_EXECUTE_MAX_OUTPUT", "8000")))
    search_timeout: int = field(default_factory=lambda: int(os.environ.get("AGENT_SEARCH_TIMEOUT", "15")))
    search_max_lines: int = field(default_factory=lambda: int(os.environ.get("AGENT_SEARCH_MAX_LINES", "50")))

    # ── 行为约束 ──────────────────────────────────
    doom_loop_window: int = field(default_factory=lambda: int(os.environ.get("AGENT_DOOM_LOOP_WINDOW", "10")))
    doom_loop_threshold: int = field(default_factory=lambda: int(os.environ.get("AGENT_DOOM_LOOP_THRESHOLD", "3")))
    max_reminder_count: int = field(default_factory=lambda: int(os.environ.get("AGENT_MAX_REMINDER_COUNT", "3")))
    step_limit: int = field(default_factory=lambda: int(os.environ.get("AGENT_STEP_LIMIT", "15")))

    # ── Reviewer 配置 ─────────────────────────────
    review_max_rounds: int = field(default_factory=lambda: int(os.environ.get("AGENT_REVIEW_MAX_ROUNDS", "2")))
    temperature_review: float = field(default_factory=lambda: float(os.environ.get("AGENT_TEMPERATURE_REVIEW", "0.1")))

    # ── 日志 ──────────────────────────────────────
    log_file: str = field(default_factory=lambda: os.environ.get("AGENT_LOG_FILE", "logs/agent.log"))


# 全局单例
_config: AgentConfig | None = None


def get_config() -> AgentConfig:
    """获取全局配置单例。"""
    global _config
    if _config is None:
        _config = AgentConfig()
    return _config


def reset_config() -> None:
    """重置配置（测试用）。"""
    global _config
    _config = None
