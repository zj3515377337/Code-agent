import json
import logging
from openai import OpenAI
from code_agent.utils.retry import retry_on_api_error

logger = logging.getLogger("code_agent.planner")


PLANNER_SYSTEM_PROMPT = """你是一个代码任务规划师。
你的工作是把用户的任务拆解成清晰的执行步骤，但你自己不执行任何操作。

输出格式要求（必须是合法 JSON）：
{
  "goal": "用一句话描述任务目标",
  "steps": [
    "步骤1：...",
    "步骤2：...",
    "步骤3：..."
  ],
  "success_criteria": "如何判断任务完成了"
}

规划原则：
1. 步骤要具体可执行，不要写"处理问题"这种模糊描述
2. 修改代码前必须有"读取文件"步骤
3. 修改代码后必须有"运行测试验证"步骤
4. 步骤数量控制在 3-7 步，不要过度拆分
"""


class Planner:
    """
    规划智能体：把任务拆解成有序步骤。

    比喻：就像施工前的"工程师"，先画好施工图纸，
    再交给"工人"（Actor）按图施工。
    规划师只负责想，不负责动手。

    来自资料 1（OPENDEV）的 Plan Mode 设计：
    Planner 只有只读权限，不能调用写工具。
    """

    def __init__(self, client: OpenAI, model: str):
        self.client = client
        self.model = model

    def plan(self, task: str) -> dict:
        """
        为任务生成结构化计划。
        返回包含 goal / steps / success_criteria 的字典。
        """
        try:
            response = self._call_planner_llm(task)
        except Exception as e:
            logger.error(f"规划 LLM 调用失败，使用降级计划: {e}")
            return self._fallback_plan(task)

        raw = response.choices[0].message.content.strip()

        try:
            plan = json.loads(raw)
            if "steps" not in plan or not isinstance(plan["steps"], list):
                raise ValueError("缺少 steps 字段")
            return plan
        except (json.JSONDecodeError, ValueError):
            logger.warning("LLM 未返回合法 JSON，使用降级计划")
            return self._fallback_plan(task)

    @retry_on_api_error(max_retries=3, base_delay=1.0)
    def _call_planner_llm(self, task: str):
        return self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
                {"role": "user",   "content": f"请为以下任务制定执行计划：\n\n{task}"}
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
        )

    @staticmethod
    def _fallback_plan(task: str) -> dict:
        return {
            "goal": task,
            "steps": [
                "步骤1：读取相关文件，了解当前代码结构",
                "步骤2：根据任务要求修改代码",
                "步骤3：运行测试验证修改是否正确"
            ],
            "success_criteria": "所有测试通过",
            "_fallback": True
        }

    @staticmethod
    def format_plan(plan: dict) -> str:
        """把计划字典格式化成可读文本，用于打印和注入对话。"""
        lines = [f"🎯 目标：{plan.get('goal', '未知')}"]
        lines.append("\n📋 执行步骤：")
        for i, step in enumerate(plan.get("steps", []), 1):
            lines.append(f"  {i}. {step}")
        if criteria := plan.get("success_criteria"):
            lines.append(f"\n✅ 完成标准：{criteria}")
        if plan.get("_fallback"):
            lines.append("\n⚠️  （使用了默认计划，LLM 未返回合法 JSON）")
        return "\n".join(lines)
