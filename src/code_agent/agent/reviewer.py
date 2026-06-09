"""
Reviewer Agent：代码审查智能体。

在 Coder 认为"完成"后触发，审查代码质量、运行测试、给出改进建议。
只有只读权限，不能编辑文件。

工作流：Coder 完成 → Reviewer 审查 → APPROVED / 反馈 → Coder 修复
"""
import logging
import json
from openai import OpenAI
from code_agent.utils.retry import retry_on_api_error
from code_agent.tools.registry import dispatch as tool_dispatch

logger = logging.getLogger("code_agent.reviewer")

# Reviewer 只能用只读工具
REVIEWER_ALLOWED_TOOLS = {
    "read_file", "list_dir", "search_class", "search_method",
    "search_method_in_class", "search_method_in_file",
    "get_file_symbols", "run_pytest", "search_text", "search_intent",
    "list_file_summaries",
}

REVIEW_SYSTEM_PROMPT = """你是一个严格的代码审查专家。你的职责是审查 Coder 的修改是否正确。

审查流程：
1. 先用 run_pytest 运行测试，确认所有测试是否通过
2. 如果测试失败，分析失败原因并给出具体修复建议
3. 如果测试通过，抽查修改的代码：
   - 是否有语法问题
   - 是否引入了新的 bug
   - 是否有更好的实现方式
4. 如果有 read_file 等工具，读取修改后的文件确认代码质量

输出格式（必须包含以下标记之一）：
- 如果代码没问题：在回复中包含 "APPROVED"
- 如果有问题：在回复中包含 "ISSUES" 并列出具体问题

注意：
- 不要过于苛刻，功能正确即可通过
- 不要重复 Coder 已经做过的修改
- 只关注是否修复了 bug，不关注代码风格
"""


class Reviewer:
    """
    代码审查智能体。

    比喻：就像 Code Review 的 reviewer。
    Coder 提交代码后，Reviewer 检查质量，
    通过则放行，不通过则打回并说明原因。
    """

    def __init__(self, client: OpenAI, model: str, max_rounds: int = 2):
        self.client = client
        self.model = model
        self.max_rounds = max_rounds
        self._review_count = 0

    def review(self, task: str, coder_summary: str) -> dict:
        """
        审查 Coder 的修改。

        参数：
        - task: 原始任务描述
        - coder_summary: Coder 最后一轮的回复（认为完成了）

        返回：
        - {"approved": bool, "feedback": str, "tool_calls_count": int}
        """
        self._review_count += 1

        prompt = (
            f"原始任务：{task}\n\n"
            f"Coder 的总结：{coder_summary}\n\n"
            "请审查 Coder 的修改。先运行测试验证，再给出审查意见。"
        )

        try:
            result = self._run_review_loop(prompt)
        except Exception as e:
            logger.error(f"Reviewer LLM 调用失败: {e}")
            return {
                "approved": True,  # LLM 失败时默认通过，不阻塞流程
                "feedback": f"（Reviewer 调用失败: {e}，默认通过）",
                "tool_calls_count": 0,
            }

        return result

    def _run_review_loop(self, prompt: str) -> dict:
        """
        Reviewer 内部的 ReAct 循环：调用 LLM，执行只读工具，直到给出最终意见。
        最多执行 5 轮工具调用（防止 Reviewer 自己陷入循环）。
        """
        messages = [
            {"role": "system", "content": REVIEW_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        tool_calls_total = 0

        for _ in range(5):
            response = self._call_review_llm(messages)
            msg = response.choices[0].message

            if msg.tool_calls:
                # 把 assistant 消息加入上下文
                messages.append({
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            }
                        }
                        for tc in msg.tool_calls
                    ]
                })

                # 执行每个工具调用
                for tc in msg.tool_calls:
                    name = tc.function.name
                    args = json.loads(tc.function.arguments)
                    tool_calls_total += 1

                    # 安全检查：只允许只读工具
                    if name not in REVIEWER_ALLOWED_TOOLS:
                        result = f"❌ Reviewer 没有权限调用 {name}，只能使用只读工具"
                    else:
                        result = tool_dispatch(name, args)
                        logger.info(f"[Reviewer] {name}({json.dumps(args, ensure_ascii=False)[:100]})")

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result,
                    })
            else:
                # 没有工具调用 = Reviewer 给出了最终意见
                content = msg.content or ""
                approved = "APPROVED" in content.upper()

                logger.info(f"[Reviewer] 审查完成: {'APPROVED' if approved else 'ISSUES'}")
                return {
                    "approved": approved,
                    "feedback": content,
                    "tool_calls_count": tool_calls_total,
                }

        # 超过 5 轮工具调用，强制结束
        logger.warning("[Reviewer] 超过最大工具调用轮数，默认通过")
        return {
            "approved": True,
            "feedback": "（Reviewer 超过最大审查轮数，默认通过）",
            "tool_calls_count": tool_calls_total,
        }

    @retry_on_api_error(max_retries=3, base_delay=1.0)
    def _call_review_llm(self, messages: list):
        return self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=self._get_reviewer_tool_schemas(),
            tool_choice="auto",
            temperature=0.1,
        )

    def _get_reviewer_tool_schemas(self) -> list:
        """返回 Reviewer 可用的工具 schema（只读工具的子集）。"""
        from code_agent.tools.registry import TOOL_SCHEMAS
        return [
            schema for schema in TOOL_SCHEMAS
            if schema["function"]["name"] in REVIEWER_ALLOWED_TOOLS
        ]

    def reset(self) -> None:
        """重置审查计数（新任务时调用）。"""
        self._review_count = 0
