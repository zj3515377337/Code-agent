import json
import os
import logging
from pathlib import Path
from typing import Callable
from openai import OpenAI
from code_agent.config import get_config
from code_agent.tools.registry import TOOL_SCHEMAS, dispatch, init_index
from code_agent.agent.planner import Planner
from code_agent.agent.reflector import Reflector
from code_agent.agent.reminder import Reminder
from code_agent.agent.reviewer import Reviewer
from code_agent.memory.working import WorkingMemory
from code_agent.memory.episodic import EpisodicMemory
from code_agent.memory.compactor import Compactor
from code_agent.utils.retry import retry_on_api_error
from code_agent.utils.logging import setup_logging

logger = logging.getLogger("code_agent")


SYSTEM_PROMPT = """你是一个代码助手，能够通过调用工具完成编程任务。

工作原则：
1. 修改已有文件时，先用 read_file 读取内容，再用 str_replace 精确替换，不要直接覆盖整个文件
2. 查找类或函数时，优先用 search_class / search_method，比 search_text 更精确
3. 不确定文件结构时，先用 get_file_symbols 查看文件里有哪些类和函数
4. 修改代码后，用 run_pytest 验证是否通过测试
5. 严格按照计划的步骤顺序执行，每次只做一件事
6. 当前运行环境是 Windows，不要使用 head/tail/grep/sed/awk 等 Linux 命令，用 Python 或 read_file 代替
"""


def _get_client() -> OpenAI:
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    if not api_key:
        raise ValueError("请在 .env 文件中设置 DEEPSEEK_API_KEY")
    return OpenAI(api_key=api_key, base_url=base_url)


@retry_on_api_error(max_retries=3, base_delay=1.0)
def _call_llm_with_retry(client: OpenAI, model: str, messages: list) -> object:
    """带重试的 LLM 调用（非流式）。"""
    return client.chat.completions.create(
        model=model,
        messages=messages,
        tools=TOOL_SCHEMAS,
        tool_choice="auto"
    )


def _stream_llm_response(client: OpenAI, model: str, messages: list,
                          on_chunk: Callable | None = None) -> object:
    """
    流式 LLM 调用。逐 token 返回文本内容，实时回调。
    返回完整的 ChatCompletion 对象（兼容非流式接口）。

    on_chunk(text_so_far) 在每个文本 chunk 时调用。
    """
    stream = client.chat.completions.create(
        model=model,
        messages=messages,
        tools=TOOL_SCHEMAS,
        tool_choice="auto",
        stream=True,
    )

    # 累积结果
    content_acc = ""
    tool_calls_acc = {}  # index -> {id, function: {name, arguments}}
    finish_reason = None

    for chunk in stream:
        delta = chunk.choices[0].delta if chunk.choices else None
        if not delta:
            continue

        # 累积文本内容
        if delta.content:
            content_acc += delta.content
            if on_chunk:
                on_chunk(content_acc)

        # 累积 tool_calls
        if delta.tool_calls:
            for tc_delta in delta.tool_calls:
                idx = tc_delta.index
                if idx not in tool_calls_acc:
                    tool_calls_acc[idx] = {
                        "id": tc_delta.id or "",
                        "type": "function",
                        "function": {"name": "", "arguments": ""}
                    }
                if tc_delta.id:
                    tool_calls_acc[idx]["id"] = tc_delta.id
                if tc_delta.function:
                    if tc_delta.function.name:
                        tool_calls_acc[idx]["function"]["name"] = tc_delta.function.name
                    if tc_delta.function.arguments:
                        tool_calls_acc[idx]["function"]["arguments"] += tc_delta.function.arguments

        if chunk.choices[0].finish_reason:
            finish_reason = chunk.choices[0].finish_reason

    # 构造兼容的响应对象
    class FakeMessage:
        def __init__(self):
            self.content = content_acc or None
            self.tool_calls = None
            if tool_calls_acc:
                sorted_tcs = [tool_calls_acc[k] for k in sorted(tool_calls_acc.keys())]
                self.tool_calls = []
                for tc_data in sorted_tcs:
                    tc = type("ToolCall", (), {
                        "id": tc_data["id"],
                        "type": "function",
                        "function": type("Function", (), {
                            "name": tc_data["function"]["name"],
                            "arguments": tc_data["function"]["arguments"],
                        })()
                    })()
                    self.tool_calls.append(tc)

    class FakeChoice:
        def __init__(self):
            self.message = FakeMessage()
            self.finish_reason = finish_reason

    class FakeResponse:
        def __init__(self):
            self.choices = [FakeChoice()]

    return FakeResponse()


def _emit(on_event: Callable | None, event_type: str, data: dict) -> None:
    """发送事件到回调，或打印到控制台。"""
    if on_event:
        on_event(event_type, data)
    else:
        _default_print(event_type, data)


def _default_print(event_type: str, data: dict) -> None:
    """默认的控制台输出。"""
    if event_type == "index":
        print(data["message"])
    elif event_type == "task_start":
        print(f"\n🎯 任务：{data['task']}\n")
    elif event_type == "plan":
        print("⏳ 正在生成执行计划...\n")
        print(data["plan_text"])
        print()
    elif event_type == "step":
        print(f"--- 第 {data['step']} 轮思考 ---")
    elif event_type == "reminder":
        print(f"⚠️  {data['hint'][:100]}")
    elif event_type == "reflect":
        print(f"🔄 触发反思（第 {data['count']}/{data['max']} 次）")
    elif event_type == "reflect_exhausted":
        print("\n⚠️  反思次数已耗尽，无法自动修复，请人工介入。")
    elif event_type == "tool_call":
        print(f"🔧 调用工具：{data['name']}")
        print(f"   参数：{data['args_short']}")
    elif event_type == "tool_result":
        print(f"📋 结果：{data['result_short']}\n")
    elif event_type == "llm_reply":
        print(f"\n✨ Agent：{data['content']}")
        print("\n✅ 任务完成！")
    elif event_type == "done":
        pass  # 打印已在 llm_reply 中完成
    elif event_type == "max_steps":
        print(f"\n⚠️  已达到最大轮次（{data['max_steps']}），任务可能未完成。")
    elif event_type == "llm_error":
        print(f"\n❌ LLM 调用失败: {data['error']}")
    elif event_type == "ablation":
        print("[ablation] Planner 已关闭，直接执行\n")
    elif event_type == "review_start":
        print(f"\n🔍 Reviewer 开始审查（第 {data['round']} 轮）...")
    elif event_type == "review_approved":
        print(f"✅ Reviewer 审查通过")
    elif event_type == "review_feedback":
        print(f"🔄 Reviewer 反馈（第 {data['round']} 轮）：{data['feedback'][:150]}")
    elif event_type == "llm_stream":
        pass  # 控制台不打印流式输出（会刷屏），由 Web UI 处理


def run(task: str, repo_root: str = ".",
        use_planner: bool = True,
        use_reflector: bool = True,
        use_reminder: bool = True,
        use_reviewer: bool = True,
        on_event: Callable | None = None) -> dict:
    """
    Agent 主入口。

    参数：
    - on_event: 可选回调函数 (event_type: str, data: dict) -> None
      不传则使用控制台输出。传入后所有事件走回调，方便 Web UI 接入。

    返回：执行结果摘要 dict。
    """
    client = _get_client()
    cfg = get_config()
    model = cfg.model

    setup_logging(log_file=cfg.log_file)
    logger.info(f"任务开始: {task[:100]}")

    # ── 解析 repo_root 为绝对路径 ─────────────────
    repo_root = str(Path(repo_root).resolve())
    logger.info(f"工作目录: {repo_root}")

    # ── 建立 AST 索引 ─────────────────────────────
    _emit(on_event, "index", {"message": f"🔍 正在扫描项目结构...\n{init_index(repo_root)}"})

    # ── 初始化模块 ────────────────────────────────
    working   = WorkingMemory(max_rounds=cfg.working_max_rounds)
    episodic  = EpisodicMemory()
    compactor = Compactor(working, episodic)
    reflector = Reflector(client, model) if use_reflector else None
    reminder  = Reminder() if use_reminder else None
    reviewer  = Reviewer(client, model, max_rounds=cfg.review_max_rounds) if use_reviewer else None
    working.set_system(SYSTEM_PROMPT)

    # ── 规划 ──────────────────────────────────────
    _emit(on_event, "task_start", {"task": task})
    plan_text = ""

    if use_planner:
        _emit(on_event, "plan", {"plan_text": "生成中..."})
        planner   = Planner(client, model)
        plan      = planner.plan(task)
        plan_text = Planner.format_plan(plan)
        _emit(on_event, "plan", {"plan_text": plan_text})
        working.append({
            "role": "user",
            "content": (
                f"任务：{task}\n\n"
                f"请按以下计划执行：\n{plan_text}\n\n"
                "请从第一步开始，逐步完成所有步骤。"
            )
        })
    else:
        _emit(on_event, "ablation", {})
        working.append({
            "role": "user",
            "content": f"请完成以下任务，用工具一步步执行：\n\n{task}"
        })

    # ── ReAct 主循环 ──────────────────────────────
    last_observation = ""
    last_reply = ""
    tool_count = 0
    review_round = 0  # 当前步骤的审查轮次
    result_summary = {"status": "running", "steps": 0, "tool_calls": 0, "reviews": 0}

    for step in range(cfg.max_steps):
        _emit(on_event, "step", {"step": step + 1})
        logger.debug(f"=== 第 {step + 1} 轮 ===")

        # 行为约束检查
        if reminder:
            hint = reminder.check(step, last_observation, last_reply)
            if hint:
                working.append({"role": "user", "content": hint})
                _emit(on_event, "reminder", {"hint": hint})

        # 反思自修复
        if reflector and last_observation and reflector.should_reflect(last_observation):
            history_parts = []
            for m in working.get_messages()[-6:]:
                if isinstance(m, dict):
                    content = m.get("content") or ""
                else:
                    content = getattr(m, "content", "") or ""
                if isinstance(content, str) and content:
                    history_parts.append(content)
            history_text = "\n".join(history_parts)
            reflect_hint = reflector.reflect(task, history_text, last_observation)
            working.append({"role": "user", "content": reflect_hint})
            _emit(on_event, "reflect", {
                "count": reflector._retry_count, "max": reflector.MAX_RETRIES
            })

        if reflector and reflector.exhausted():
            _emit(on_event, "reflect_exhausted", {})
            result_summary["status"] = "reflect_exhausted"
            break

        # 压缩 + LLM 调用
        compactor.compress(client, model)
        messages = compactor.get_full_context()

        try:
            if on_event:
                # 流式调用：逐 token 回调，实时显示
                def _on_stream_chunk(text_so_far):
                    _emit(on_event, "llm_stream", {"text": text_so_far})
                response = _stream_llm_response(client, model, messages, _on_stream_chunk)
            else:
                response = _call_llm_with_retry(client, model, messages)
        except Exception as e:
            logger.error(f"LLM 调用最终失败: {e}")
            _emit(on_event, "llm_error", {"error": str(e)})
            result_summary["status"] = "llm_error"
            break

        msg = response.choices[0].message

        if msg.tool_calls:
            working.append({
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in msg.tool_calls
                ]
            })

            for tool_call in msg.tool_calls:
                name = tool_call.function.name
                try:
                    args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError as e:
                    logger.error(f"工具参数 JSON 解析失败: {e}")
                    working.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": f"❌ 工具参数解析失败: {e}"
                    })
                    continue

                args_short = json.dumps(args, ensure_ascii=False)[:80]
                _emit(on_event, "tool_call", {"name": name, "args_short": args_short})
                logger.info(f"工具调用: {name}({args_short})")

                if name == "search_text" and "task_hint" not in args:
                    args["task_hint"] = task

                result = dispatch(name, args)
                last_observation = result
                tool_count += 1
                result_short = result[:150] + ("..." if len(result) > 150 else "")
                _emit(on_event, "tool_result", {"result_short": result_short})

                if reminder:
                    reminder.record_tool_call(name, args)

                working.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result
                })

            if reflector and last_observation.startswith("✅"):
                reflector.reset()

        else:
            last_reply = msg.content or ""
            logger.info(f"Coder 认为完成，进入审查阶段")

            # ── Reviewer 审查（可关闭）────────────────
            if reviewer and review_round < cfg.review_max_rounds:
                _emit(on_event, "review_start", {"round": review_round + 1})
                review_result = reviewer.review(task, last_reply)
                review_round += 1
                result_summary["reviews"] += 1

                if review_result["approved"]:
                    _emit(on_event, "review_approved", {
                        "feedback": review_result["feedback"][:200],
                        "tool_calls": review_result["tool_calls_count"],
                    })
                    _emit(on_event, "llm_reply", {"content": msg.content})
                    logger.info(f"Reviewer 通过，任务完成")
                    result_summary["status"] = "completed"
                    break
                else:
                    # 审查不通过，注入反馈让 Coder 继续修复
                    feedback_msg = (
                        f"[Reviewer 审查反馈（第 {review_round} 轮）]\n"
                        f"{review_result['feedback']}\n"
                        f"请根据以上反馈修复问题，修复后再次汇报结果。"
                    )
                    working.append({"role": "user", "content": feedback_msg})
                    _emit(on_event, "review_feedback", {
                        "round": review_round,
                        "feedback": review_result["feedback"][:300],
                    })
                    logger.info(f"Reviewer 反馈第 {review_round} 轮，Coder 继续修复")
                    # 不 break，继续下一轮 ReAct
            else:
                # 无 Reviewer 或审查轮次耗尽，直接完成
                _emit(on_event, "llm_reply", {"content": msg.content})
                if reviewer:
                    logger.info(f"审查轮次耗尽，默认通过")
                else:
                    logger.info(f"任务完成，共 {step + 1} 轮")
                result_summary["status"] = "completed"
                break
    else:
        _emit(on_event, "max_steps", {"max_steps": cfg.max_steps})
        logger.warning(f"达到最大轮次 {cfg.max_steps}")
        result_summary["status"] = "max_steps"

    result_summary["steps"] = step + 1
    result_summary["tool_calls"] = tool_count
    result_summary["plan"] = plan_text
    _emit(on_event, "done", result_summary)
    return result_summary
