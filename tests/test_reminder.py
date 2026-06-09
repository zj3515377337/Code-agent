"""Reminder 模块单元测试。"""
import pytest
from code_agent.agent.reminder import Reminder


@pytest.fixture
def rm():
    return Reminder()


# ── 死循环检测 ──────────────────────────────────────

class TestDoomLoop:
    def test_no_doom_loop_with_different_calls(self, rm):
        """不同的工具调用不应触发死循环提醒。"""
        for i in range(5):
            rm.record_tool_call("read_file", {"path": f"file_{i}.py"})
        assert rm._check_doom_loop() is None

    def test_doom_loop_triggers_on_repeated_call(self, rm):
        """完全相同的调用重复 3 次应触发死循环提醒。"""
        for _ in range(3):
            rm.record_tool_call("read_file", {"path": "same.py"})
        result = rm._check_doom_loop()
        assert result is not None
        assert "重复" in result

    def test_doom_loop_max_reminders(self, rm):
        """死循环提醒最多触发 MAX_REMINDER_COUNT 次。"""
        # 先构造死循环条件（3 次相同调用）
        for _ in range(3):
            rm.record_tool_call("read_file", {"path": "same.py"})
        # 触发 MAX_REMINDER_COUNT 次提醒
        for _ in range(rm.MAX_REMINDER_COUNT):
            rm._check_doom_loop()
        # 超过上限后不再提醒
        assert rm._check_doom_loop() is None


# ── 过早提交检测 ──────────────────────────────────

class TestPrematureCompletion:
    def test_no_reminder_when_no_completion_signal(self, rm):
        """LLM 没说"完成"时不提醒。"""
        assert rm._check_premature_completion("我正在分析代码...") is None

    def test_reminder_when_done_without_pytest(self, rm):
        """LLM 说"完成"但没跑过 pytest 时应提醒。"""
        result = rm._check_premature_completion("任务完成！所有修改已就绪。")
        assert result is not None
        assert "run_pytest" in result

    def test_no_reminder_when_pytest_ran(self, rm):
        """跑过 pytest 后说"完成"不应提醒。"""
        rm.record_tool_call("run_pytest", {})
        assert rm._check_premature_completion("任务完成！") is None

    def test_premature_completion_max_count(self, rm):
        """过早提交提醒最多触发 MAX_REMINDER_COUNT 次。"""
        for _ in range(rm.MAX_REMINDER_COUNT):
            rm._check_premature_completion("已完成")
        assert rm._check_premature_completion("已完成") is None


# ── 上下文收集不足检测 ────────────────────────────

class TestMissingTestContext:
    def test_no_reminder_at_step_2(self, rm):
        """第 2 轮不触发检查。"""
        rm.record_tool_call("str_replace", {"path": "code.py"})
        rm.record_tool_call("str_replace", {"path": "code.py"})
        assert rm._check_missing_test_context(2) is None

    def test_reminder_at_step_3_without_reading_test(self, rm):
        """第 3 轮已编辑但没读测试文件时应提醒。"""
        rm.record_tool_call("str_replace", {"path": "code.py"})
        rm.record_tool_call("str_replace", {"path": "code.py"})
        rm.record_tool_call("str_replace", {"path": "code.py"})
        result = rm._check_missing_test_context(3)
        assert result is not None
        assert "test" in result.lower()

    def test_no_reminder_if_test_was_read(self, rm):
        """读过测试文件后不应提醒。"""
        rm.record_tool_call("read_file", {"path": "test_code.py"})
        rm.record_tool_call("str_replace", {"path": "code.py"})
        rm.record_tool_call("str_replace", {"path": "code.py"})
        assert rm._check_missing_test_context(3) is None

    def test_no_reminder_if_no_editing_yet(self, rm):
        """没编辑过代码时不提醒（只是在搜索/阅读）。"""
        rm.record_tool_call("search_text", {"pattern": "bug"})
        rm.record_tool_call("read_file", {"path": "code.py"})
        rm.record_tool_call("search_class", {"class_name": "Foo"})
        assert rm._check_missing_test_context(3) is None


# ── 步数提醒 ──────────────────────────────────────

class TestStepLimit:
    def test_reminder_at_step_15(self, rm):
        """第 15 步应提醒。"""
        result = rm._check_step_limit(15)
        assert result is not None
        assert "15" in result

    def test_no_reminder_at_step_14(self, rm):
        """第 14 步不提醒。"""
        assert rm._check_step_limit(14) is None

    def test_no_reminder_at_step_16(self, rm):
        """第 16 步不重复提醒（只在 15 触发一次）。"""
        rm._check_step_limit(15)  # 第一次触发
        assert rm._check_step_limit(16) is None


# ── check() 集成 ───────────────────────────────────

class TestCheckIntegration:
    def test_check_returns_none_when_no_issues(self, rm):
        """没有异常时返回 None。"""
        rm.record_tool_call("read_file", {"path": "code.py"})
        assert rm.check(1, "读取成功", "正在分析...") is None

    def test_check_priority_premature_over_doom(self, rm):
        """过早提交优先级高于死循环检测。"""
        # 构造死循环条件
        for _ in range(3):
            rm.record_tool_call("read_file", {"path": "same.py"})
        # 同时 LLM 说完成
        result = rm.check(3, "结果", "任务完成")
        assert result is not None
        assert "run_pytest" in result  # 应该是过早提交提醒


# ── record_tool_call ────────────────────────────────

class TestRecordToolCall:
    def test_tracks_pytest_execution(self, rm):
        """记录 run_pytest 调用。"""
        assert rm._ran_pytest is False
        rm.record_tool_call("run_pytest", {})
        assert rm._ran_pytest is True

    def test_tracks_test_file_reading(self, rm):
        """记录读取测试文件。"""
        assert rm._read_test_file is False
        rm.record_tool_call("read_file", {"path": "test_calculator.py"})
        assert rm._read_test_file is True

    def test_non_test_file_not_tracked(self, rm):
        """非测试文件不标记。"""
        rm.record_tool_call("read_file", {"path": "calculator.py"})
        assert rm._read_test_file is False

    def test_stats(self, rm):
        """stats() 返回正确的统计信息。"""
        rm.record_tool_call("read_file", {"path": "test.py"})
        rm.record_tool_call("run_pytest", {})
        s = rm.stats()
        assert s["step_count"] == 2
        assert s["ran_pytest"] is True
        assert s["read_test_file"] is True
