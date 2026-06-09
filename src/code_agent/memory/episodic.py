from openai import OpenAI


class EpisodicMemory:
    """
    长期情景记忆：把旧的对话历史压缩成一段简短的文字摘要保存下来。

    比喻：就像你做完一件事后写的"工作日志"。
    不需要记住每一句话，只需要记住"做了什么、结果怎样"。
    下次继续工作时，先看一眼日志，就能快速恢复上下文。
    """

    # 摘要最多保留的字符数（来自资料 1：500 字符摘要）
    MAX_SUMMARY_CHARS = 500

    def __init__(self):
        self._summary: str = ""

    def has_summary(self) -> bool:
        return bool(self._summary)

    def get_summary(self) -> str:
        return self._summary

    def get_as_message(self) -> dict | None:
        """把摘要包装成一条 user 消息，插入对话历史最前面。"""
        if not self._summary:
            return None
        return {
            "role": "user",
            "content": f"[之前的工作摘要]\n{self._summary}\n[摘要结束，继续当前任务]"
        }

    def compress(self, messages: list[dict], client: OpenAI, model: str) -> str:
        """
        调用 LLM 把一段对话历史压缩成摘要，存入 _summary。
        返回生成的摘要文本。
        """
        if not messages:
            return ""

        # 把消息列表转成纯文本，方便 LLM 理解
        history_text = _messages_to_text(messages)

        prompt = (
            f"请把以下对话历史压缩成不超过 {self.MAX_SUMMARY_CHARS} 字的摘要。\n"
            "重点保留：完成了哪些步骤、修改了哪些文件、测试结果如何、还有哪些未完成。\n"
            "不需要保留具体的代码内容。\n\n"
            f"对话历史：\n{history_text}"
        )

        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
        )

        self._summary = response.choices[0].message.content.strip()
        return self._summary


def _messages_to_text(messages: list) -> str:
    """把消息列表转成可读文本，兼容 dict 和 ChatCompletionMessage 两种类型。"""
    lines = []
    for msg in messages:
        if isinstance(msg, dict):
            role = msg.get("role", "unknown")
            content = msg.get("content") or ""
        else:
            role = getattr(msg, "role", "unknown")
            content = getattr(msg, "content", "") or ""
        # tool 消息内容可能很长，截断一下
        if role == "tool":
            content = content[:200] + "..." if len(content) > 200 else content
        if content:
            lines.append(f"[{role}]: {content}")
    return "\n".join(lines)
