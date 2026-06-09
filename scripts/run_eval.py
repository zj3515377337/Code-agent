"""
评测脚本：支持 Agent 模式 vs 基线模式（裸 LLM）对比。

运行方式：
  cd d:\\Run\\study\\代码智能体\\code-agent
  set PYTHONPATH=src
  python scripts/run_eval.py                # 仅跑 Agent
  python scripts/run_eval.py --baseline     # 同时跑基线对比
  python scripts/run_eval.py --ablation     # 跑消融实验
"""
import sys
import os
import json
import time
import re
import shutil
import subprocess
import argparse
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from code_agent.actor import run as agent_run

TASKS_DIR   = PROJECT_ROOT / "evaluation" / "tasks"
RESULTS_DIR = PROJECT_ROOT / "evaluation" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


# ── 评测配置 ────────────────────────────────────────
CONFIGS = {
    "agent_full": {
        "use_planner": True, "use_reflector": True, "use_reminder": True, "use_reviewer": True,
        "description": "完整 Agent（Plan + Reflect + Remind + Review）"
    },
    "baseline": {
        "use_planner": False, "use_reflector": False, "use_reminder": False, "use_reviewer": False,
        "description": "基线（裸 LLM，无任何模块）"
    },
    "no_planner": {
        "use_planner": False, "use_reflector": True, "use_reminder": True, "use_reviewer": True,
        "description": "去掉 Planner"
    },
    "no_reflector": {
        "use_planner": True, "use_reflector": False, "use_reminder": True, "use_reviewer": True,
        "description": "去掉 Reflector"
    },
    "no_reminder": {
        "use_planner": True, "use_reflector": True, "use_reminder": False, "use_reviewer": True,
        "description": "去掉 Reminder"
    },
    "no_reviewer": {
        "use_planner": True, "use_reflector": True, "use_reminder": True, "use_reviewer": False,
        "description": "去掉 Reviewer"
    },
}


def run_pytest_in_dir(task_dir: Path) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-v", "--tb=short", str(task_dir)],
            capture_output=True, text=True, timeout=60,
            encoding="utf-8", errors="replace",
            cwd=str(task_dir)
        )
        return result.returncode == 0, result.stdout + "\n" + result.stderr
    except subprocess.TimeoutExpired:
        return False, "测试超时"
    except Exception as e:
        return False, f"运行错误：{e}"


def parse_pytest_summary(output: str) -> dict:
    summary = {"passed": 0, "failed": 0, "total": 0}
    for key in ["passed", "failed"]:
        m = re.search(rf"(\d+)\s+{key}", output)
        if m:
            summary[key] = int(m.group(1))
    summary["total"] = summary["passed"] + summary["failed"]
    return summary


def backup_task(task_dir: Path) -> Path:
    backup = task_dir.parent / f".{task_dir.name}.backup"
    if backup.exists():
        shutil.rmtree(backup)
    shutil.copytree(task_dir, backup)
    return backup


def restore_task(task_dir: Path, backup: Path) -> None:
    if task_dir.exists():
        shutil.rmtree(task_dir)
    shutil.copytree(backup, task_dir)
    shutil.rmtree(backup)


def run_single_task(task_dir: Path, config: dict) -> dict:
    task_name = task_dir.name
    task_file = task_dir / "task.txt"
    if not task_file.exists():
        return {"task": task_name, "status": "skip"}

    task_text = task_file.read_text(encoding="utf-8").strip()
    backup = backup_task(task_dir)

    start_time = time.time()
    try:
        full_task = (
            f"请修复 {task_dir} 目录下的代码 bug，让该目录下所有测试通过。\n"
            f"具体要求：{task_text}"
        )
        agent_run(
            full_task,
            repo_root=str(task_dir),
            use_planner=config["use_planner"],
            use_reflector=config["use_reflector"],
            use_reminder=config["use_reminder"],
            use_reviewer=config.get("use_reviewer", True),
        )
        agent_status = "completed"
    except Exception as e:
        agent_status = f"error: {e}"
    elapsed = time.time() - start_time

    post_pass, post_output = run_pytest_in_dir(task_dir)
    post_stats = parse_pytest_summary(post_output)

    restore_task(task_dir, backup)

    return {
        "task": task_name,
        "status": "pass" if post_pass else "fail",
        "agent_status": agent_status,
        "elapsed_sec": round(elapsed, 1),
        "post_passed": post_stats["passed"],
        "post_failed": post_stats["failed"],
        "total_tests": post_stats["total"],
    }


def run_config_group(config_name: str, config: dict, task_dirs: list) -> list[dict]:
    print(f"\n{'='*70}")
    print(f"🧪 配置：{config_name} - {config['description']}")
    print(f"{'='*70}")

    results = []
    for task_dir in task_dirs:
        print(f"\n  📋 {task_dir.name}...", end=" ", flush=True)
        try:
            result = run_single_task(task_dir, config)
            emoji = "✅" if result["status"] == "pass" else "❌"
            print(f"{emoji} ({result.get('elapsed_sec', '?')}s)")
            results.append(result)
        except Exception as e:
            print(f"💥 {e}")
            results.append({"task": task_dir.name, "status": "error"})
    return results


def generate_report(all_results: dict[str, list[dict]]) -> str:
    lines = [
        "# Code Agent 评测报告",
        f"\n生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "\n## 总览对比\n",
        "| 配置 | 描述 | 通过率 | 通过/总数 | 平均耗时 |",
        "| --- | --- | --- | --- | --- |",
    ]

    for config_name, results in all_results.items():
        total = len(results)
        passed = sum(1 for r in results if r.get("status") == "pass")
        rate = passed / total * 100 if total else 0
        avg_time = sum(r.get("elapsed_sec", 0) for r in results) / total if total else 0
        desc = CONFIGS.get(config_name, {}).get("description", config_name)
        lines.append(f"| **{config_name}** | {desc} | **{rate:.0f}%** | {passed}/{total} | {avg_time:.1f}s |")

    # 模块贡献分析
    if "agent_full" in all_results and len(all_results) > 1:
        full_results = all_results["agent_full"]
        full_passed = sum(1 for r in full_results if r.get("status") == "pass")
        full_rate = full_passed / len(full_results) * 100

        lines.append("\n## 模块贡献分析\n")
        lines.append("| 配置 | 通过率 | 相对完整版 |")
        lines.append("| --- | --- | --- |")
        lines.append(f"| **agent_full** | {full_rate:.0f}% | — |")

        for config_name, results in all_results.items():
            if config_name == "agent_full":
                continue
            passed = sum(1 for r in results if r.get("status") == "pass")
            rate = passed / len(results) * 100
            delta = full_rate - rate
            sign = "↓" if delta > 0 else "↑" if delta < 0 else "="
            lines.append(f"| {config_name} | {rate:.0f}% | {sign}{abs(delta):.0f}% |")

    # 逐任务详情
    lines.append("\n## 逐任务详情\n")
    lines.append("| 任务 | " + " | ".join(all_results.keys()) + " |")
    lines.append("| --- | " + " | ".join(["---"] * len(all_results)) + " |")

    # 按任务名聚合
    task_names = sorted(set(
        r["task"] for results in all_results.values() for r in results
    ))
    for task_name in task_names:
        cells = []
        for config_name in all_results:
            result = next(
                (r for r in all_results[config_name] if r["task"] == task_name),
                None
            )
            if result:
                emoji = "✅" if result["status"] == "pass" else "❌"
                cells.append(f"{emoji} {result.get('elapsed_sec', '?')}s")
            else:
                cells.append("—")
        lines.append(f"| {task_name} | {' | '.join(cells)} |")

    return "\n".join(lines)


def generate_visualization(all_results: dict[str, list[dict]], output_dir: Path) -> None:
    """生成 matplotlib 可视化图表。"""
    try:
        import matplotlib.pyplot as plt
        import matplotlib
        matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
        matplotlib.rcParams['axes.unicode_minus'] = False
    except ImportError:
        print("⚠️  matplotlib 未安装，跳过可视化")
        return

    configs = list(all_results.keys())
    pass_rates = []
    avg_times = []

    for config_name in configs:
        results = all_results[config_name]
        total = len(results)
        passed = sum(1 for r in results if r.get("status") == "pass")
        pass_rates.append(passed / total * 100 if total else 0)
        avg_times.append(
            sum(r.get("elapsed_sec", 0) for r in results) / total if total else 0
        )

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    # 通过率柱状图
    colors = ['#2ecc71' if c == 'agent_full' else '#3498db' for c in configs]
    bars1 = ax1.bar(configs, pass_rates, color=colors)
    ax1.set_ylabel('通过率 (%)')
    ax1.set_title('不同配置的通过率对比')
    ax1.set_ylim(0, 105)
    for bar, rate in zip(bars1, pass_rates):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                f'{rate:.0f}%', ha='center', va='bottom')
    ax1.tick_params(axis='x', rotation=30)

    # 平均耗时柱状图
    bars2 = ax2.bar(configs, avg_times, color=colors)
    ax2.set_ylabel('平均耗时 (秒)')
    ax2.set_title('不同配置的平均耗时对比')
    for bar, t in zip(bars2, avg_times):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                f'{t:.1f}s', ha='center', va='bottom')
    ax2.tick_params(axis='x', rotation=30)

    plt.tight_layout()
    chart_path = output_dir / "eval_chart.png"
    plt.savefig(chart_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"📊 可视化图表：{chart_path}")


def main():
    parser = argparse.ArgumentParser(description="Code Agent 评测脚本")
    parser.add_argument("--baseline", action="store_true", help="同时跑基线对比")
    parser.add_argument("--ablation", action="store_true", help="跑完整消融实验（4 组）")
    parser.add_argument("--tasks", type=str, help="只跑指定任务目录，逗号分隔")
    args = parser.parse_args()

    # 选择要跑的配置
    if args.ablation:
        run_configs = {k: v for k, v in CONFIGS.items()}
    elif args.baseline:
        run_configs = {"agent_full": CONFIGS["agent_full"], "baseline": CONFIGS["baseline"]}
    else:
        run_configs = {"agent_full": CONFIGS["agent_full"]}

    # 选择任务
    if args.tasks:
        task_dirs = [TASKS_DIR / t.strip() for t in args.tasks.split(",")]
    else:
        task_dirs = sorted([
            d for d in TASKS_DIR.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        ])

    print("\n" + "="*70)
    print("🤖 Code Agent 评测开始")
    print("="*70)
    print(f"📂 任务数：{len(task_dirs)}")
    print(f"🧪 配置数：{len(run_configs)}")
    print(f"🧪 配置：{', '.join(run_configs.keys())}")

    all_results = {}
    for config_name, config in run_configs.items():
        all_results[config_name] = run_config_group(config_name, config, task_dirs)

    # 保存结果
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = RESULTS_DIR / f"results_{timestamp}.json"
    json_path.write_text(
        json.dumps(all_results, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    print(f"\n💾 原始结果：{json_path}")

    # 生成报告
    report = generate_report(all_results)
    report_path = RESULTS_DIR / f"report_{timestamp}.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"📊 报告：{report_path}")

    # 可视化
    generate_visualization(all_results, RESULTS_DIR)

    # 打印总览
    print("\n" + "="*70)
    print(report)


if __name__ == "__main__":
    main()
