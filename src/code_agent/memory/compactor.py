"""
上下文压缩调度器：按 Token 数（而非消息条数）触发压缩。

粗略估算：中文 2 字符/token，英文/代码 4 字符/token，取 3.5 折中。
精确方案用 tiktoken，当前版本用估算避免额外依赖。
"""
from openai import OpenAI
from code_agent.memory.working import WorkingMemory
from code_agent.memory.episodic import EpisodicMemory
from code_agent.config import get_config


def estimate_tokens(messages: list[dict]) -> int:
    """
    估算消息列表的 token 数。
    使用 1 token ≈ 3.5 字符的粗略估算（DeepSeek tokenizer 的折中值）。
    """
    total = 0
    for msg in messages:
        content = msg.get("content") or ""
        if isinstance(content, str):
            total += len(content) / 3.5
        # tool_calls 也占 token
        tool_calls = msg.get("tool_calls") or []
        for tc in tool_calls:
            func = tc.get("function") if isinstance(tc, dict) else getattr(tc, "function", None)
            if func:
                name = func.get("name") if isinstance(func, dict) else getattr(func, "name", "")
                args = func.get("arguments") if isinstance(func, dict) else getattr(func, "arguments", "")
                total += len(str(name)) / 3.5 + len(str(args)) / 3.5
    return int(total)


class Compactor:
    """
    上下文压缩调度器：按 Token 数触发压缩。

    来自资料 1（OPENDEV）的 5 阶段渐进压缩设计，
    原版按消息条数触发，本版升级为按 Token 数触发（更精确）。
    """

    def __init__(self, working: WorkingMemory, episodic: EpisodicMemory):
        self.working = working
        self.episodic = episodic
        self._compress_count = 0

    def should_compress(self) -> bool:
        """判断是否需要压缩：Token 数超过阈值时返回 True。"""
        cfg = get_config()
        messages = self.working.get_messages()
        tokens = estimate_tokens(messages)
        return tokens >= cfg.compress_token_threshold

    def compress(self, client: OpenAI, model: str) -> bool:
        """
        执行一次压缩：
        1. 把当前历史压缩成摘要存入 episodic memory
        2. 清理 working memory，只保留最近 ~2000 token 的消息
        返回是否实际执行了压缩。
        """
        if not self.should_compress():
            return False

        cfg = get_config()
        messages = self.working.get_messages()
        current_tokens = estimate_tokens(messages)
        print(f"\n[compaction] Token 数 {current_tokens} 超过阈值 {cfg.compress_token_threshold}，开始压缩...")

        # 调用 LLM 生成摘要
        self.episodic.compress(messages, client, model)

        # 按 Token 数清理旧消息：保留最后 ~keep_after_compress_tokens 的消息
        # 从后向前逐条累加，直到达到目标 token 数
        recent_only = self.working._messages[:]  # 不含 system
        keep_count = 0
        token_sum = 0
        for msg in reversed(recent_only):
            token_sum += estimate_tokens([msg])
            keep_count += 1
            if token_sum >= cfg.keep_after_compress_tokens:
                break

        removed = self.working.clear_old(keep_last=max(keep_count, 4))
        self._compress_count += 1

        new_tokens = estimate_tokens(self.working.get_messages())
        print(f"[compaction] 完成：清理了 {removed} 条旧消息，"
              f"Token {current_tokens} → {new_tokens}，已压缩 {self._compress_count} 次")
        return True

    def get_full_context(self) -> list[dict]:
        """
        返回完整上下文：episodic 摘要（如有）+ working memory 最近消息。
        """
        messages = self.working.get_messages()

        summary_msg = self.episodic.get_as_message()
        if summary_msg and len(messages) > 1:
            return [messages[0], summary_msg] + messages[1:]

        return messages
