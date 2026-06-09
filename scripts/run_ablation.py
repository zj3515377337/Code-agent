"""
消融实验评测脚本：对比完整版 vs 去掉某个模块的通过率差异。

运行方式：
  cd d:\\Run\\study\\代码智能体\\code-agent
  set PYTHONPATH=src
  python scripts/run_ablation.py

会依次跑 4 组实验：
  1. full:         完整版（Planner + Reflector + Reminder）
  2. no_planner:   去掉 Planner
  3. no_reflector: 去掉 Reflector
  4. no_reminder:  去掉 Reminder

每组跑 10 个任务，生成对比报告。
"""
import sys
import os
import json
import time
import shutil
import subprocess
import re
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


# ── 消融配置 ──────────────────────────────────────────
ABLATION_CONFIGS = {
    "full": {
        "use_planner": True,
        "use_reflector": True,
        "use_reminder": True,
        "description": "完整版（Plan + Reflect + Remind）"
    },
    "no_planner": {
        "use_planner": False,
        "use_reflector": True,
        "use_reminder": True,
        "description": "去掉 Planner（直接执行，不做规划）"
    },
    "no_reflector": {
        "use_planner": True,
        "use_reflector": False,
        "use_reminder": True,
        "description": "去掉 Reflector（失败不反思，不重试）"
    },
    "no_reminder": {
        "use_planner": True,
        "use_reflector": True,
        "use_reminder": False,
        "description": "去掉 Reminder（不检查行为约束）"
    },
}


def run_pytest_in_dir(task_dir: Path) -> tuple[bool, str]:
    """在指定目录跑 pytest。"""
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
    """从 pytest 输出提取通过/失败数量。"""
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
    """用指定配置跑单个任务。"""
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
        "elapsed_sec": round(elapsed, 1),
        "post_passed": post_stats["passed"],
        "post_failed": post_stats["failed"],
        "total_tests": post_stats["total"],
    }


def run_ablation_group(config_name: str, config: dict) -> list[dict]:
    """跑一组消融实验。"""
    print(f"\n{'='*70}")
    print(f"🧪 消融实验：{config_name} - {config['description']}")
    print(f"{'='*70}")

    task_dirs = sorted([d for d in TASKS_DIR.iterdir() if d.is_dir()])
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


def generate_ablation_report(all_results: dict[str, list[dict]]) -> str:
    """生成消融实验对比报告。"""
    lines = [
        "# Code Agent 消融实验报告",
        f"\n生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "\n## 实验目的",
        "\n通过逐一关闭系统模块，量化每个模块对整体通过率的贡献。",
        "\n## 总览对比\n",
        "| 配置 | 描述 | 通过率 | 通过/总数 | 平均耗时 |",
        "| --- | --- | --- | --- | --- |",
    ]

    for config_name, results in all_results.items():
        total = len(results)
        passed = sum(1 for r in results if r.get("status") == "pass")
        rate = passed / total * 100 if total else 0
        avg_time = sum(r.get("elapsed_sec", 0) for r in results) / total if total else 0
        desc = ABLATION_CONFIGS[config_name]["description"]
        lines.append(f"| **{config_name}** | {desc} | **{rate:.0f}%** | {passed}/{total} | {avg_time:.1f}s |")

    # 计算每个模块的贡献
    full_pass = sum(1 for r in all_results.get("full", []) if r.get("status") == "pass")
    lines.append("\n## 模块贡献分析\n")
    lines.append("| 模块 | 关闭后通过率变化 | 贡献度 |")
    lines.append("| --- | --- | --- |")

    for config_name in ["no_planner", "no_reflector", "no_reminder"]:
        if config_name in all_results:
            results = all_results[config_name]
            total = len(results)
            passed = sum(1 for r in results if r.get("status") == "pass")
            rate = passed / total * 100 if total else 0
            full_rate = full_pass / len(all_results.get("full", [1])) * 100
            delta = full_rate - rate
            module = config_name.replace("no_", "")
            lines.append(f"| {module} | {full_rate:.0f}% → {rate:.0f}% (↓{delta:.0f}%) | **{delta:.0f}%** |")

    lines.append("\n## 结论\n")
    lines.append("通过率下降越多，说明该模块对系统贡献越大。")

    return "\n".join(lines)


def main():
    print("\n" + "="*70)
    print("🧪 Code Agent 消融实验开始")
    print("="*70)
    print(f"📂 任务目录：{TASKS_DIR}")
    print(f"🧪 实验组数：{len(ABLATION_CONFIGS)}")
    print(f"⏱️  预计耗时：{len(ABLATION_CONFIGS) * 10 * 20 // 60} 分钟（每任务约 20s）")

    all_results = {}
    for config_name, config in ABLATION_CONFIGS.items():
        all_results[config_name] = run_ablation_group(config_name, config)

    # 保存原始结果
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = RESULTS_DIR / f"ablation_{timestamp}.json"
    json_path.write_text(
        json.dumps(all_results, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    print(f"\n💾 原始结果：{json_path}")

    # 生成报告
    report = generate_ablation_report(all_results)
    report_path = RESULTS_DIR / f"ablation_report_{timestamp}.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"📊 报告：{report_path}")

    # 打印总览
    print("\n" + "="*70)
    print(report)


if __name__ == "__main__":
    main()
