"""Reviewer Agent 单元测试。"""
import pytest
import sys
from unittest.mock import MagicMock, patch

sys.modules.setdefault("openai", MagicMock())
from code_agent.agent.reviewer import Reviewer, REVIEWER_ALLOWED_TOOLS


class TestReviewerInit:
    def test_default_max_rounds(self):
        client = MagicMock()
        r = Reviewer(client, "test-model")
        assert r.max_rounds == 2

    def test_custom_max_rounds(self):
        client = MagicMock()
        r = Reviewer(client, "test-model", max_rounds=3)
        assert r.max_rounds == 3

    def test_reset(self):
        client = MagicMock()
        r = Reviewer(client, "test-model")
        r._review_count = 5
        r.reset()
        assert r._review_count == 0


class TestReviewerToolFiltering:
    def test_allowed_tools_are_readonly(self):
        """Reviewer 只能用只读工具，不能用编辑工具。"""
        assert "read_file" in REVIEWER_ALLOWED_TOOLS
        assert "run_pytest" in REVIEWER_ALLOWED_TOOLS
        assert "search_class" in REVIEWER_ALLOWED_TOOLS
        # 编辑工具不在列表中
        assert "write_file" not in REVIEWER_ALLOWED_TOOLS
        assert "str_replace" not in REVIEWER_ALLOWED_TOOLS
        assert "replace_function" not in REVIEWER_ALLOWED_TOOLS
        assert "execute" not in REVIEWER_ALLOWED_TOOLS

    def test_get_reviewer_tool_schemas(self):
        """返回的 schema 只包含允许的工具。"""
        client = MagicMock()
        r = Reviewer(client, "test-model")
        schemas = r._get_reviewer_tool_schemas()
        names = {s["function"]["name"] for s in schemas}
        assert "read_file" in names
        assert "write_file" not in names
        assert "str_replace" not in names


class TestReviewerReview:
    def test_approved_when_llm_says_approved(self):
        """LLM 回复包含 APPROVED 时返回 approved=True。"""
        client = MagicMock()
        r = Reviewer(client, "test-model")

        # Mock LLM response - no tool calls, text contains APPROVED
        mock_msg = MagicMock()
        mock_msg.tool_calls = None
        mock_msg.content = "所有测试通过，代码质量良好。APPROVED"

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=mock_msg)]

        client.chat.completions.create.return_value = mock_response

        result = r.review("fix the bug", "I fixed the divide function")
        assert result["approved"] is True
        assert "APPROVED" in result["feedback"]

    def test_issues_when_llm_says_issues(self):
        """LLM 回复包含 ISSUES 时返回 approved=False。"""
        client = MagicMock()
        r = Reviewer(client, "test-model")

        mock_msg = MagicMock()
        mock_msg.tool_calls = None
        mock_msg.content = "ISSUES: 测试未通过，divide 函数仍有 bug"

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=mock_msg)]

        client.chat.completions.create.return_value = mock_response

        result = r.review("fix the bug", "I think it's done")
        assert result["approved"] is False
        assert "ISSUES" in result["feedback"]

    def test_approved_on_llm_failure(self):
        """LLM 调用失败时默认通过，不阻塞流程。"""
        client = MagicMock()
        r = Reviewer(client, "test-model")

        client.chat.completions.create.side_effect = Exception("API Error")

        result = r.review("fix the bug", "done")
        assert result["approved"] is True
        assert "失败" in result["feedback"]

    def test_review_count_increments(self):
        """每次审查计数递增。"""
        client = MagicMock()
        r = Reviewer(client, "test-model")

        mock_msg = MagicMock()
        mock_msg.tool_calls = None
        mock_msg.content = "APPROVED"
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=mock_msg)]
        client.chat.completions.create.return_value = mock_response

        r.review("task", "done")
        assert r._review_count == 1
        r.review("task", "done")
        assert r._review_count == 2

    def test_review_loop_with_tool_calls(self):
        """Reviewer 内部循环：先调工具，再给最终意见。"""
        client = MagicMock()
        r = Reviewer(client, "test-model")

        # 第一次 LLM 调用：返回 tool_call (run_pytest)
        tc_mock = MagicMock()
        tc_mock.id = "tc1"
        tc_mock.function.name = "run_pytest"
        tc_mock.function.arguments = '{"path": "."}'

        msg1 = MagicMock()
        msg1.tool_calls = [tc_mock]
        msg1.content = ""

        # 第二次 LLM 调用：返回最终意见
        msg2 = MagicMock()
        msg2.tool_calls = None
        msg2.content = "测试全部通过。APPROVED"

        resp1 = MagicMock()
        resp1.choices = [MagicMock(message=msg1)]
        resp2 = MagicMock()
        resp2.choices = [MagicMock(message=msg2)]

        client.chat.completions.create.side_effect = [resp1, resp2]

        # Mock dispatch to avoid actually running pytest
        with patch("code_agent.agent.reviewer.tool_dispatch", return_value="✅ 5 passed"):
            result = r.review("fix bug", "done")

        assert result["approved"] is True
        assert result["tool_calls_count"] == 1

    def test_blocked_tool_returns_error(self):
        """Reviewer 调用编辑工具时被拒绝。"""
        client = MagicMock()
        r = Reviewer(client, "test-model")

        # LLM 尝试调用 write_file（不在允许列表中）
        tc_mock = MagicMock()
        tc_mock.id = "tc1"
        tc_mock.function.name = "write_file"
        tc_mock.function.arguments = '{"path": "x.py", "content": "bad"}'

        msg1 = MagicMock()
        msg1.tool_calls = [tc_mock]
        msg1.content = ""

        msg2 = MagicMock()
        msg2.tool_calls = None
        msg2.content = "APPROVED"

        resp1 = MagicMock()
        resp1.choices = [MagicMock(message=msg1)]
        resp2 = MagicMock()
        resp2.choices = [MagicMock(message=msg2)]

        client.chat.completions.create.side_effect = [resp1, resp2]

        result = r.review("task", "done")
        assert result["approved"] is True
        # write_file 被拒绝，tool_calls_count 仍为 1（调用了一次但被拒绝）
        assert result["tool_calls_count"] == 1
