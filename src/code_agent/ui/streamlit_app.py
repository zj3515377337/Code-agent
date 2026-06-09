"""
Code Agent - Streamlit Web UI
运行方式：
  cd d:\\Run\\study\\代码智能体\\code-agent
  set PYTHONPATH=src
  streamlit run src/code_agent/ui/streamlit_app.py
"""
import sys
import os
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent.parent / ".env")

from code_agent.actor import run as agent_run

# ── 页面配置 ────────────────────────────────────────
st.set_page_config(page_title="Code Agent", page_icon="🤖", layout="wide")
st.title("🤖 Code Agent")
st.caption("基于 LLM 的自主代码修复智能体")

# ── session_state 初始化 ────────────────────────────
if "logs" not in st.session_state:
    st.session_state.logs = []
if "running" not in st.session_state:
    st.session_state.running = False

# ── 侧边栏配置 ──────────────────────────────────────
with st.sidebar:
    st.header("⚙️ 配置")
    model = st.selectbox("模型", ["deepseek-chat", "gpt-4o-mini"], index=0)
    repo_root = st.text_input("项目根目录", value=".")
    max_steps = st.slider("最大执行轮次", 5, 30, 20)
    use_reviewer = st.checkbox("启用 Reviewer 审查", value=True)
    st.divider()
    st.markdown("**快速任务示例**")
    examples = [
        ("string_utils", "examples/m6_real_bugs/string_utils.py 有 bug，请读取测试文件了解期望行为，修复所有 bug，只修改 string_utils.py，让 test_string_utils.py 全部通过"),
        ("date_utils",   "examples/m6_real_bugs/date_utils.py 有 bug，请读取测试文件了解期望行为，修复所有 bug，只修改 date_utils.py，让 test_date_utils.py 全部通过"),
        ("stats_utils",  "examples/m6_real_bugs/stats_utils.py 有 bug，请读取测试文件了解期望行为，修复所有 bug，只修改 stats_utils.py，让 test_stats_utils.py 全部通过"),
    ]
    for label, task_text in examples:
        if st.button(label, use_container_width=True):
            st.session_state.task_input = task_text
            st.session_state.logs = []

# ── 任务输入 ────────────────────────────────────────
task = st.text_area(
    "输入任务",
    value=st.session_state.get("task_input", ""),
    height=80,
    placeholder="例如：examples/m6_real_bugs/string_utils.py 有 bug，请修复并让测试通过"
)

col_run, col_clear = st.columns([4, 1])
run_btn   = col_run.button("▶ 开始执行", type="primary", use_container_width=True)
clear_btn = col_clear.button("🗑 清空", use_container_width=True)

if clear_btn:
    st.session_state.logs = []
    st.rerun()

# ── 执行区域 ────────────────────────────────────────
if run_btn and task.strip():
    st.session_state.task_input = task
    st.session_state.logs = []

if st.session_state.logs or (run_btn and task.strip()):
    st.divider()

    # 指标行
    stat1, stat2, stat3 = st.columns(3)
    step_metric   = stat1.empty()
    tool_metric   = stat2.empty()
    status_metric = stat3.empty()
    step_metric.metric("⚡ 执行轮次", 0)
    tool_metric.metric("🔧 工具调用", 0)
    status_metric.metric("📌 状态", "等待中")

    st.divider()

    # 计划 + 日志并排
    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown("#### 📋 执行计划")
        plan_placeholder = st.empty()
        plan_placeholder.info("等待生成计划...")
    with col2:
        st.markdown("#### 🔄 执行过程")
        log_placeholder = st.container(height=450)

    # 非新执行时只展示历史日志
    if not run_btn:
        with log_placeholder:
            for line in st.session_state.logs:
                st.markdown(line)
        st.stop()

    # ── 事件回调：将 agent 事件转为 UI 更新 ─────────
    step_count = [0]
    tool_count = [0]
    stream_placeholder = [None]  # 流式输出占位符

    # 创建流式输出区域
    with col2:
        stream_area = st.empty()

    def on_event(event_type: str, data: dict):
        icons = {
            "info": "ℹ️", "tool_call": "🔧", "tool_result": "📋",
            "reflect": "🔄", "warn": "⚠️", "llm_reply": "✅",
            "reminder": "⚠️", "plan": "📋",
        }

        if event_type == "step":
            step_count[0] = data["step"]
            step_metric.metric("⚡ 执行轮次", step_count[0])

        elif event_type == "plan":
            plan_placeholder.markdown(data["plan_text"])

        elif event_type == "tool_call":
            tool_count[0] += 1
            tool_metric.metric("🔧 工具调用", tool_count[0])
            icon = icons.get("tool_call", "•")
            msg = f"**{data['name']}** `{data['args_short']}`"
            st.session_state.logs.append(f"{icon} {msg}")
            with log_placeholder:
                st.markdown(f"{icon} {msg}")

        elif event_type == "tool_result":
            icon = icons.get("tool_result", "•")
            st.session_state.logs.append(f"{icon} {data['result_short']}")
            with log_placeholder:
                st.markdown(f"{icon} {data['result_short']}")

        elif event_type == "reflect":
            icon = icons.get("reflect", "•")
            msg = f"触发反思（第 {data['count']}/{data['max']} 次）"
            st.session_state.logs.append(f"{icon} {msg}")
            with log_placeholder:
                st.markdown(f"{icon} {msg}")

        elif event_type == "reminder":
            icon = icons.get("reminder", "•")
            st.session_state.logs.append(f"{icon} 系统提醒已注入")
            with log_placeholder:
                st.markdown(f"{icon} 系统提醒已注入")

        elif event_type == "llm_reply":
            icon = icons.get("llm_reply", "•")
            msg = f"**Agent 总结：** {data['content'][:300]}"
            st.session_state.logs.append(f"{icon} {msg}")
            with log_placeholder:
                st.markdown(f"{icon} {msg}")
            status_metric.metric("📌 状态", "✅ 完成")
            st.success("✅ 任务完成！")

        elif event_type == "reflect_exhausted":
            status_metric.metric("📌 状态", "需人工介入")
            st.warning("反思次数耗尽，请人工介入")

        elif event_type == "max_steps":
            status_metric.metric("📌 状态", "⚠️ 超时")
            st.warning("已达到最大轮次，任务可能未完成。")

        elif event_type == "llm_error":
            status_metric.metric("📌 状态", "❌ 错误")
            st.error(f"LLM 调用失败: {data['error']}")

        elif event_type == "index":
            st.success(data["message"])

        elif event_type == "task_start":
            status_metric.metric("📌 状态", "运行中")
            step_metric.metric("⚡ 执行轮次", 0)
            tool_metric.metric("🔧 工具调用", 0)
            st.session_state.logs.append(f"ℹ️ 任务开始：{data['task'][:80]}...")

        elif event_type == "review_start":
            st.session_state.logs.append(f"🔍 Reviewer 审查（第 {data['round']} 轮）...")
            with log_placeholder:
                st.markdown(f"🔍 Reviewer 审查（第 {data['round']} 轮）...")

        elif event_type == "review_approved":
            st.session_state.logs.append("✅ Reviewer 审查通过")
            with log_placeholder:
                st.markdown("✅ Reviewer 审查通过")

        elif event_type == "review_feedback":
            feedback_short = data['feedback'][:200]
            st.session_state.logs.append(f"🔄 Reviewer 反馈（第 {data['round']} 轮）：{feedback_short}")
            with log_placeholder:
                st.markdown(f"🔄 Reviewer 反馈（第 {data['round']} 轮）：{feedback_short}")

        elif event_type == "llm_stream":
            # 流式输出：实时更新 Agent 的文本回复
            stream_area.markdown(f"✨ **Agent：** {data['text']}")

    # ── 设置环境变量并执行 ─────────────────────────
    os.environ["AGENT_MODEL"] = model
    os.environ["AGENT_MAX_STEPS"] = str(max_steps)

    with st.spinner("正在执行任务..."):
        agent_run(
            task,
            repo_root=repo_root,
            use_reviewer=use_reviewer,
            on_event=on_event,
        )

elif run_btn:
    st.warning("请先输入任务内容。")
