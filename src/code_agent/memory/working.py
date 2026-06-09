from typing import Any


class WorkingMemory:
    
    """
    短期工作记忆：保存最近 N 轮的完整对话历史。

    比喻：就像人做事时的"工作台"，只放当前正在用的东西。
    工作台太小放不下太多，所以只保留最近的 N 轮对话。
    """

    def __init__(self, max_rounds: int = 6):
        # max_rounds：最多保留几轮对话（1轮 = 1次用户消息 + 1次LLM回复）
        self.max_rounds = max_rounds
        self._messages: list[dict[str, Any]] = []
        # system prompt 单独保存，永远不会被压缩掉
        self._system: dict[str, Any] | None = None

    def set_system(self, content: str) -> None:
        """设置系统提示词，只设置一次。"""
        self._system = {"role": "system", "content": content}

    def append(self, message: dict[str, Any]) -> None:
        """添加一条消息到历史。"""
        self._messages.append(message)

    def get_messages(self) -> list[dict[str, Any]]:
        """
        返回当前完整的消息列表（system + 最近 N 轮）。
        超出 max_rounds 的旧消息会被丢弃。
        """
        # 计算要保留的消息数量
        # 每轮大约 2-4 条消息（user + assistant + tool results）
        # 保守估计每轮 4 条，保留 max_rounds 轮
        keep = self.max_rounds * 4
        recent = self._messages[-keep:] if len(self._messages) > keep else self._messages

        if self._system:
            return [self._system] + recent
        return recent

    def count(self) -> int:
        """返回当前消息总数（不含 system）。"""
        return len(self._messages)

    def clear_old(self, keep_last: int = 4) -> int:
        """
        主动清理旧消息，只保留最后 keep_last 条。
        清理后自动删除开头的孤立 tool 消息（前面没有 assistant(tool_calls)）。
        返回被清理的消息数量。
        """
        if len(self._messages) <= keep_last:
            return 0
        removed = len(self._messages) - keep_last
        self._messages = self._messages[-keep_last:]

        # 删除开头的孤立 tool 消息（前面没有 assistant(tool_calls)）
        while self._messages and self._messages[0].get("role") == "tool":
            self._messages.pop(0)
            removed += 1

        return removed
