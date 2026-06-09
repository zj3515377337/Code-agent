import logging
from openai import OpenAI
from code_agent.utils.retry import retry_on_api_error

logger = logging.getLogger("code_agent.reflector")


REFLECT_SYSTEM_PROMPT = """你是一个代码调试专家，负责分析失败原因并给出修复建议。

分析时请关注：
1. 错误类型（语法错误、逻辑错误、测试失败、工具调用失败）
2. 错误发生在哪个文件哪一行
3. 最可能的根本原因
4. 具体的修复步骤（要可执行，不要模糊建议）

输出格式：
- 错误分析：（1-2句话说清楚出了什么问题）
- 修复方案：（具体的操作步骤，比如"读取 X 文件第 Y 行，将 Z 改为 W"）
"""


class Reflector:
    """
    反思自修复模块：分析失败原因，生成修复 hint 注入对话。

    比喻：就像有经验的 code reviewer。
    工人（Actor）做错了，reviewer 不是骂人，
    而是指出"第13行逻辑反了，应该改成这样"，
    工人按建议重新来过。

    来自资料 1（OPENDEV）self-critique 设计 +
    资料 9（SICA）异步 Overseer 思路。
    """

    MAX_RETRIES = 3  # 同一错误最多反思重试几次（资料 1 经验阈值）

    def __init__(self, client: OpenAI, model: str):
        self.client = client
        self.model = model
        self._retry_count = 0
        self._last_error: str = ""

    def should_reflect(self, observation: str) -> bool:
        """
        判断工具输出是否表示失败，需要触发反思。
        失败信号：以 ❌ 开头，或包含 pytest 失败标志。
        """
        if self._retry_count >= self.MAX_RETRIES:
            return False
        failure_signals = ["❌", "FAILED", "failed", "Error", "Traceback"]
        return any(sig in observation for sig in failure_signals)

    def reflect(self, task: str, history_summary: str, error_output: str) -> str:
        """
        分析失败原因，返回修复 hint 字符串。
        以 role:user 注入对话——来自资料 1 教训 2：
        role:user 注入比 role:system 合规率显著更高。
        """
        self._retry_count += 1
        self._last_error = error_output

        prompt = (
            f"当前任务：{task}\n\n"
            f"已完成步骤摘要：\n{history_summary}\n\n"
            f"最新错误输出：\n{error_output}\n\n"
            "请分析失败原因并给出具体修复方案。"
        )

        try:
            response = self._call_reflect_llm(prompt)
        except Exception as e:
            logger.error(f"反思 LLM 调用失败: {e}")
            return (
                f"[反思提醒 {self._retry_count}/{self.MAX_RETRIES}]\n"
                f"（反思模块 LLM 调用失败: {e}）\n"
                f"请尝试换一种方式修复。"
            )

        hint = response.choices[0].message.content.strip()
        return (
            f"[反思提醒 {self._retry_count}/{self.MAX_RETRIES}]\n"
            f"{hint}\n"
            f"请根据以上分析继续修复，不要重复之前失败的操作。"
        )

    @retry_on_api_error(max_retries=3, base_delay=1.0)
    def _call_reflect_llm(self, prompt: str):
        return self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": REFLECT_SYSTEM_PROMPT},
                {"role": "user",   "content": prompt}
            ],
            temperature=0.2,
            max_tokens=400,
        )

    def reset(self) -> None:
        """任务成功后重置计数器。"""
        self._retry_count = 0
        self._last_error = ""

    def exhausted(self) -> bool:
        """是否已用完所有重试次数。"""
        return self._retry_count >= self.MAX_RETRIES
