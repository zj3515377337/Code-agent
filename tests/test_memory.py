"""记忆模块单元测试（WorkingMemory + Compactor）。"""
import pytest
import sys
from unittest.mock import MagicMock, patch
from code_agent.memory.working import WorkingMemory

# episodic.py 顶层导入 openai，测试环境可能没装，用 mock 绕过
sys.modules.setdefault("openai", MagicMock())
from code_agent.memory.episodic import EpisodicMemory
from code_agent.memory.compactor import Compactor, estimate_tokens


# ── WorkingMemory ───────────────────────────────────

class TestWorkingMemory:
    def test_append_and_get(self):
        wm = WorkingMemory(max_rounds=3)
        wm.set_system("system prompt")
        wm.append({"role": "user", "content": "hello"})
        msgs = wm.get_messages()
        assert len(msgs) == 2  # system + user
        assert msgs[0]["role"] == "system"
        assert msgs[1]["content"] == "hello"

    def test_system_always_first(self):
        wm = WorkingMemory(max_rounds=3)
        wm.set_system("sys")
        for i in range(20):
            wm.append({"role": "user", "content": f"msg {i}"})
        msgs = wm.get_messages()
        assert msgs[0]["role"] == "system"

    def test_count_excludes_system(self):
        """count() 只统计 _messages，不含 system。"""
        wm = WorkingMemory(max_rounds=3)
        wm.set_system("sys")
        assert wm.count() == 0  # system 不计入
        wm.append({"role": "user", "content": "a"})
        assert wm.count() == 1

    def test_clear_old(self):
        wm = WorkingMemory(max_rounds=3)
        wm.set_system("sys")
        for i in range(10):
            wm.append({"role": "user", "content": f"msg {i}"})
        removed = wm.clear_old(keep_last=3)
        assert removed == 7
        assert wm.count() == 3  # 只保留 3 条 _messages
        assert len(wm.get_messages()) == 4  # system + 3

    def test_messages_are_dicts(self):
        """确保返回的消息都是 dict 类型（不会泄漏 ChatCompletionMessage）。"""
        wm = WorkingMemory(max_rounds=3)
        wm.set_system("sys")
        wm.append({"role": "assistant", "content": "hi", "tool_calls": []})
        for m in wm.get_messages():
            assert isinstance(m, dict)

    def test_clear_old_removes_orphan_tool_messages(self):
        """清理后开头的孤立 tool 消息应被删除，避免 API 报错。"""
        wm = WorkingMemory(max_rounds=10)
        wm.set_system("sys")
        # 模拟 assistant(tool_calls) -> tool(result) 配对
        wm.append({"role": "user", "content": "task"})
        wm.append({"role": "assistant", "content": "", "tool_calls": [{"id": "t1", "type": "function", "function": {"name": "read_file", "arguments": "{}"}}]})
        wm.append({"role": "tool", "tool_call_id": "t1", "content": "file content"})
        wm.append({"role": "assistant", "content": "", "tool_calls": [{"id": "t2", "type": "function", "function": {"name": "str_replace", "arguments": "{}"}}]})
        wm.append({"role": "tool", "tool_call_id": "t2", "content": "replace ok"})
        wm.append({"role": "assistant", "content": "done"})

        # 保留最后 3 条：tool(t2), assistant(tool_calls:t2), assistant("done")
        # 但 tool(t2) 是孤立的（前面的 assistant(tool_calls:t2) 被保留了）
        # 实际上保留 4 条：assistant(tool_calls:t2), tool(t2), assistant("done")
        # 如果保留 3 条：tool(t2), assistant(tool_calls:t2), assistant("done") -> tool 是孤立的
        removed = wm.clear_old(keep_last=3)
        msgs = wm.get_messages()
        # 开头不应是 tool 消息
        assert msgs[0]["role"] != "tool" or msgs[0].get("tool_call_id") is None
        # 验证 API 格式正确：每个 tool 前面都有 assistant(tool_calls)
        for i, m in enumerate(msgs):
            if m.get("role") == "tool" and i > 0:
                prev = msgs[i - 1]
                assert prev.get("role") == "assistant" and prev.get("tool_calls"), \
                    f"孤立的 tool 消息在位置 {i}"


# ── Token 估算 ─────────────────────────────────────

class TestEstimateTokens:
    def test_empty_list(self):
        assert estimate_tokens([]) == 0

    def test_english_text(self):
        tokens = estimate_tokens([{"role": "user", "content": "Hello world"}])
        assert 2 <= tokens <= 5  # ~11 chars / 3.5 ≈ 3

    def test_chinese_text(self):
        tokens = estimate_tokens([{"role": "user", "content": "你好世界"}])
        assert 1 <= tokens <= 3  # ~4 chars / 3.5 ≈ 1

    def test_tool_calls_counted(self):
        msgs = [{
            "role": "assistant",
            "content": "",
            "tool_calls": [{
                "id": "t1",
                "type": "function",
                "function": {"name": "read_file", "arguments": '{"path": "x.py"}'}
            }]
        }]
        tokens = estimate_tokens(msgs)
        assert tokens > 0  # tool call 也占 token

    def test_long_message_higher_token_count(self):
        short = [{"role": "user", "content": "hi"}]
        long = [{"role": "user", "content": "a" * 1000}]
        assert estimate_tokens(long) > estimate_tokens(short) * 10


# ── Compactor ───────────────────────────────────────

class TestCompactor:
    def test_should_not_compress_empty(self):
        """空消息列表不应触发压缩。"""
        wm = WorkingMemory(max_rounds=10)
        wm.set_system("sys")
        ep = EpisodicMemory()
        compactor = Compactor(wm, ep)
        # 只有 system prompt，token 数远低于阈值
        assert compactor.should_compress() is False

    def test_should_compress_with_long_messages(self):
        """长消息超过 token 阈值应触发压缩。"""
        wm = WorkingMemory(max_rounds=100)
        wm.set_system("x" * 500)  # system 也很长
        # 添加很多长消息
        for i in range(30):
            wm.append({"role": "user", "content": "x" * 500})
        ep = EpisodicMemory()
        compactor = Compactor(wm, ep)
        # 30 * 500 / 3.5 ≈ 4285 + system 143 = ~4428 tokens，可能还不到 8000
        # 再加 30 条
        for i in range(30):
            wm.append({"role": "assistant", "content": "y" * 500})
        # 现在应该有 ~8800 tokens
        assert compactor.should_compress() is True

    def test_get_full_context_without_summary(self):
        wm = WorkingMemory(max_rounds=10)
        wm.set_system("sys")
        wm.append({"role": "user", "content": "hello"})
        ep = EpisodicMemory()
        compactor = Compactor(wm, ep)
        ctx = compactor.get_full_context()
        assert len(ctx) == 2
        assert ctx[0]["role"] == "system"

    def test_get_full_context_with_summary(self):
        wm = WorkingMemory(max_rounds=10)
        wm.set_system("sys")
        wm.append({"role": "user", "content": "hello"})
        wm.append({"role": "assistant", "content": "hi"})
        ep = EpisodicMemory()
        ep._summary = "之前的对话摘要"
        compactor = Compactor(wm, ep)
        ctx = compactor.get_full_context()
        assert len(ctx) == 4
        assert ctx[1]["role"] == "user"
        assert "摘要" in ctx[1]["content"]
