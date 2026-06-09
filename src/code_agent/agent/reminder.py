import hashlib
from collections import deque
from code_agent.config import get_config


class Reminder:
    """
    事件驱动的提醒注入器：检测异常模式，在决策点注入简短提醒。

    来自资料 1（OPENDEV）§3.3 的核心设计：
    - 提醒以 role:user 注入（实验证明合规率显著更高）
    - 每类提醒有次数上限，避免变成噪声
    - 在决策点之前注入，而非提前布道

    P1 新增（来自论文 Behavioral Drivers of Coding Agent Success and Failure）：
    - 检测"过早提交"：LLM 说完成但还没跑过 pytest
    - 检测"上下文收集不足"：前 3 轮没有读过测试文件
    """

    def __init__(self):
        cfg = get_config()
        self.DOOM_LOOP_WINDOW    = cfg.doom_loop_window
        self.DOOM_LOOP_THRESHOLD = cfg.doom_loop_threshold
        self.MAX_REMINDER_COUNT  = cfg.max_reminder_count
        self.STEP_LIMIT          = cfg.step_limit

        self._tool_fingerprints: deque = deque(maxlen=self.DOOM_LOOP_WINDOW)
        self._reminder_counts: dict[str, int] = {}
        self._step_count = 0

        # P1 新增：行为追踪
        self._ran_pytest      = False   # 是否跑过 pytest
        self._read_test_file  = False   # 是否读过测试文件
        self._tools_called: list[str] = []  # 所有工具调用历史

    def record_tool_call(self, tool_name: str, tool_args: dict) -> None:
        """记录每次工具调用，用于死循环检测和行为约束检查。"""
        self._step_count += 1
        self._tools_called.append(tool_name)

        # 追踪关键行为
        if tool_name in ("run_pytest", "execute"):
            self._ran_pytest = True
        if tool_name == "read_file":
            path = tool_args.get("path", "")
            if "test" in path.lower():
                self._read_test_file = True

        # MD5 指纹用于死循环检测
        fingerprint = hashlib.md5(
            f"{tool_name}:{sorted(tool_args.items())}".encode()
        ).hexdigest()[:8]
        self._tool_fingerprints.append(fingerprint)

    def check(self, step: int, last_observation: str = "",
              last_reply: str = "") -> str | None:
        """
        在每轮决策前调用，检查是否需要注入提醒。
        last_reply：LLM 上一轮的文字回复（用于检测过早提交）。
        返回提醒文本，无需提醒返回 None。
        """
        # 检查顺序：行为约束 > 死循环 > 步数
        reminder = self._check_premature_completion(last_reply)
        if reminder:
            return reminder

        reminder = self._check_missing_test_context(step)
        if reminder:
            return reminder

        reminder = self._check_doom_loop()
        if reminder:
            return reminder

        reminder = self._check_step_limit(step)
        if reminder:
            return reminder

        return None

    # ── P1 新增：行为约束检测 ──────────────────────────

    def _check_premature_completion(self, last_reply: str) -> str | None:
        """
        检测"过早提交"：LLM 说完成了但还没跑过 pytest。
        来自论文：过早提交是最常见的失败模式之一。
        """
        if not last_reply:
            return None

        # 检测 LLM 是否在说"完成"相关的词
        completion_signals = ["完成", "修复完毕", "已修复", "全部通过", "任务完成",
                              "done", "fixed", "completed", "all tests pass"]
        said_done = any(s in last_reply.lower() for s in completion_signals)

        if said_done and not self._ran_pytest:
            key = "premature_completion"
            if self._reminder_counts.get(key, 0) >= self.MAX_REMINDER_COUNT:
                return None
            self._reminder_counts[key] = self._reminder_counts.get(key, 0) + 1
            print(f"\n[behavior_check] 检测到过早提交，注入提醒")
            return (
                "[系统提醒] 你说任务完成了，但还没有运行测试验证。\n"
                "请先调用 run_pytest 确认所有测试通过，再给出最终总结。"
            )
        return None

    def _check_missing_test_context(self, step: int) -> str | None:
        """
        检测"上下文收集不足"：前 3 轮没有读过测试文件就开始修改代码。
        来自论文：不了解测试期望就修代码，成功率显著更低。
        """
        # 只在第 3 轮检查一次
        if step != 3:
            return None

        # 如果已经读过测试文件，不需要提醒
        if self._read_test_file:
            return None

        # 如果已经调用过编辑工具，说明没读测试就开始改了
        edit_tools = {"str_replace", "write_file", "tool_replace_function"}
        already_editing = any(t in edit_tools for t in self._tools_called)
        if not already_editing:
            return None

        key = "missing_test_context"
        if self._reminder_counts.get(key, 0) >= 1:
            return None
        self._reminder_counts[key] = 1
        print(f"\n[behavior_check] 检测到未读测试文件就开始修改，注入提醒")
        return (
            "[系统提醒] 你还没有读取测试文件就开始修改代码。\n"
            "建议先用 read_file 读取对应的 test_*.py 文件，\n"
            "了解测试期望的行为和异常类型，再进行修改，成功率会更高。"
        )

    # ── 原有检测器 ──────────────────────────────────

    def _check_doom_loop(self) -> str | None:
        """检测是否在重复做同样的操作。"""
        if len(self._tool_fingerprints) < self.DOOM_LOOP_THRESHOLD:
            return None

        recent = list(self._tool_fingerprints)[-self.DOOM_LOOP_THRESHOLD:]
        if len(set(recent)) == 1:
            key = "doom_loop"
            if self._reminder_counts.get(key, 0) >= self.MAX_REMINDER_COUNT:
                return None
            self._reminder_counts[key] = self._reminder_counts.get(key, 0) + 1
            print(f"\n[doom_loop detected] 检测到重复操作，注入提醒 "
                  f"({self._reminder_counts[key]}/{self.MAX_REMINDER_COUNT})")
            return (
                "[系统提醒] 你已经重复执行了相同的操作多次，但没有进展。\n"
                "请换一种方式：尝试不同的工具、不同的参数，或者重新读取文件确认当前状态。\n"
                "不要再重复之前失败的操作。"
            )
        return None

    def _check_step_limit(self, step: int) -> str | None:
        """步数超过阈值时提醒 Agent 聚焦。"""
        if step == self.STEP_LIMIT:
            key = "step_limit"
            if self._reminder_counts.get(key, 0) >= 1:
                return None
            self._reminder_counts[key] = 1
            print(f"\n[reminder injected] 步数提醒")
            return (
                f"[系统提醒] 你已经执行了 {self.STEP_LIMIT} 步，请检查是否偏离了原始计划。\n"
                "如果核心任务已完成，请先运行 run_pytest 验证，再给出总结。\n"
                "如果还未完成，请聚焦在最关键的剩余步骤上。"
            )
        return None

    def stats(self) -> dict:
        """返回统计信息，方便 debug。"""
        return {
            "step_count":         self._step_count,
            "ran_pytest":         self._ran_pytest,
            "read_test_file":     self._read_test_file,
            "reminder_counts":    dict(self._reminder_counts),
            "recent_fingerprints": list(self._tool_fingerprints)
        }
