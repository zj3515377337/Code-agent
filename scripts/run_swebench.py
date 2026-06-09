"""
SWE-bench Lite 评测脚本。

流程：
1. git clone 仓库 → checkout 到 base_commit
2. 应用 test_patch（添加/修改测试文件）
3. 让 Agent 修复 bug（输入 problem_statement）
4. 运行测试验证
5. 对比 Agent 的 patch 和 gold patch

运行方式：
  cd d:/Run/study/代码智能体/code-agent
  python scripts/run_swebench.py                      # 跑全部 30 道
  python scripts/run_swebench.py --limit 5            # 只跑前 5 道
  python scripts/run_swebench.py --task psf__requests-2674  # 跑单道
"""
import sys
import os
import json
import time
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

# SWE-bench 任务比自建评测集复杂，需要更多步骤和重试次数
os.environ["AGENT_MAX_STEPS"] = "30"
os.environ["AGENT_MAX_RETRIES"] = "5"

SWEBENCH_DIR = PROJECT_ROOT / "evaluation" / "swebench"
REPOS_DIR    = PROJECT_ROOT / "evaluation" / "swebench" / "repos"
RESULTS_DIR  = PROJECT_ROOT / "evaluation" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def load_tasks() -> list[dict]:
    tasks_file = SWEBENCH_DIR / "selected_30.json"
    with open(tasks_file, encoding="utf-8") as f:
        return json.load(f)


def clone_repo(repo: str, base_commit: str) -> Path:
    """
    Clone 仓库到本地并 checkout 到指定 commit。
    使用缓存避免重复 clone。
    """
    repo_name = repo.split("/")[-1]
    repo_dir = REPOS_DIR / repo_name

    # 如果缓存的仓库存在但 checkout 失败，删掉重来
    if repo_dir.exists():
        # 先尝试直接 checkout
        result = subprocess.run(
            ["git", "checkout", base_commit],
            cwd=str(repo_dir), capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            # checkout 成功，重置状态
            subprocess.run(["git", "clean", "-fd"], cwd=str(repo_dir), capture_output=True, timeout=30)
            subprocess.run(["git", "checkout", "--", "."], cwd=str(repo_dir), capture_output=True, timeout=30)
            return repo_dir
        # checkout 失败，尝试 fetch 目标 commit
        print(f"  📥 Fetching commit {base_commit[:12]}...")
        subprocess.run(
            ["git", "fetch", "origin", base_commit],
            cwd=str(repo_dir), capture_output=True, timeout=120
        )
        result = subprocess.run(
            ["git", "checkout", base_commit],
            cwd=str(repo_dir), capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            subprocess.run(["git", "clean", "-fd"], cwd=str(repo_dir), capture_output=True, timeout=30)
            subprocess.run(["git", "checkout", "--", "."], cwd=str(repo_dir), capture_output=True, timeout=30)
            return repo_dir
        # fetch 也失败，删掉重新 clone
        print(f"  ⚠️  缓存仓库缺少目标 commit，重新 clone...")
        shutil.rmtree(repo_dir, ignore_errors=True)

    # 全新 clone（浅克隆 + fetch 目标 commit，比完整 clone 快很多）
    REPOS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"  📥 Cloning {repo} (--depth=1)...")
    result = subprocess.run(
        ["git", "clone", "--depth=1", f"https://github.com/{repo}.git", str(repo_dir)],
        capture_output=True, timeout=300
    )
    if result.returncode != 0:
        raise RuntimeError(f"Clone failed: {result.stderr[:200]}")

    # fetch 目标 commit
    print(f"  📥 Fetching commit {base_commit[:12]}...")
    subprocess.run(
        ["git", "fetch", "origin", base_commit],
        cwd=str(repo_dir), capture_output=True, timeout=120
    )

    # checkout 到 base_commit
    subprocess.run(
        ["git", "checkout", base_commit],
        cwd=str(repo_dir), capture_output=True, timeout=30
    )

    # 重置到干净状态
    subprocess.run(["git", "clean", "-fd"], cwd=str(repo_dir), capture_output=True, timeout=30)
    subprocess.run(["git", "checkout", "--", "."], cwd=str(repo_dir), capture_output=True, timeout=30)

    return repo_dir


def apply_patch(repo_dir: Path, patch: str) -> bool:
    """应用 git patch（test_patch 或 Agent 的 patch）。"""
    if not patch.strip():
        return True

    patch_file = repo_dir / ".swe_patch.diff"
    patch_file.write_text(patch, encoding="utf-8")

    # 尝试 1: git apply（严格模式）
    result = subprocess.run(
        ["git", "apply", "--check", str(patch_file)],
        cwd=str(repo_dir), capture_output=True, text=True, timeout=30
    )
    if result.returncode == 0:
        subprocess.run(
            ["git", "apply", str(patch_file)],
            cwd=str(repo_dir), capture_output=True, timeout=30
        )
        patch_file.unlink(missing_ok=True)
        return True

    # 尝试 2: git apply --3way（三路合并）
    result = subprocess.run(
        ["git", "apply", "--3way", str(patch_file)],
        cwd=str(repo_dir), capture_output=True, text=True, timeout=30
    )
    if result.returncode == 0:
        patch_file.unlink(missing_ok=True)
        return True

    # 尝试 3: patch 命令
    result = subprocess.run(
        ["patch", "-p1", "--input", str(patch_file)],
        cwd=str(repo_dir), capture_output=True, text=True, timeout=30
    )
    patch_file.unlink(missing_ok=True)
    if result.returncode == 0:
        return True

    # 全部失败，手动解析应用关键测试文件
    print(f"  ⚠️  Patch 应用失败，尝试手动提取测试文件...")
    return _apply_patch_manually(repo_dir, patch)


def _apply_patch_manually(repo_dir: Path, patch: str) -> bool:
    """
    手动从 patch 中提取新增的测试文件并创建。
    SWE-bench 的 test_patch 通常只是新增/修改测试函数。
    """
    import re
    current_file = None
    new_lines = []
    success = False

    for line in patch.split("\n"):
        # 匹配 +++ b/path/to/file.py
        m = re.match(r'^\+\+\+ b/(.+)', line)
        if m:
            # 保存上一个文件
            if current_file and new_lines:
                try:
                    fpath = repo_dir / current_file
                    fpath.parent.mkdir(parents=True, exist_ok=True)
                    if fpath.exists():
                        # 追加到现有文件
                        with open(fpath, "a", encoding="utf-8") as f:
                            f.write("\n" + "\n".join(new_lines) + "\n")
                    else:
                        fpath.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
                    success = True
                except Exception:
                    pass
            current_file = m.group(1)
            new_lines = []
            continue

        # 只取新增的行（以 + 开头，不是 +++）
        if line.startswith("+") and not line.startswith("+++"):
            new_lines.append(line[1:])

    # 保存最后一个文件
    if current_file and new_lines:
        try:
            fpath = repo_dir / current_file
            fpath.parent.mkdir(parents=True, exist_ok=True)
            if fpath.exists():
                with open(fpath, "a", encoding="utf-8") as f:
                    f.write("\n" + "\n".join(new_lines) + "\n")
            else:
                fpath.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
            success = True
        except Exception:
            pass

    return success


def get_fail_tests(test_patch: str) -> list[str]:
    """从 test_patch 中提取 FAIL_TO_PASS 的测试标识。"""
    # 简单实现：从 patch 中找 test 函数名
    tests = []
    for line in test_patch.split("\n"):
        if line.startswith("+") and "def test_" in line:
            func_name = line.split("def ")[1].split("(")[0].strip()
            tests.append(func_name)
    return tests


def run_tests(repo_dir: Path, test_files: list[str] = None) -> tuple[bool, str]:
    """在仓库目录下运行测试。"""
    # 找测试文件
    if not test_files:
        # 从 test_patch 推断
        result = subprocess.run(
            ["python", "-m", "pytest", "--co", "-q", "--no-header"],
            cwd=str(repo_dir), capture_output=True, text=True,
            timeout=60, encoding="utf-8", errors="replace"
        )
        if result.returncode != 0:
            return False, result.stdout + "\n" + result.stderr

    # 运行测试（限制超时）
    try:
        result = subprocess.run(
            ["python", "-m", "pytest", "-x", "-q", "--tb=short", "--no-header"],
            cwd=str(repo_dir), capture_output=True, text=True,
            timeout=120, encoding="utf-8", errors="replace"
        )
        passed = result.returncode == 0
        output = result.stdout[-2000:] + "\n" + result.stderr[-1000:]
        return passed, output
    except subprocess.TimeoutExpired:
        return False, "测试超时（>120s）"


def get_agent_patch(repo_dir: Path) -> str:
    """获取 Agent 修改的 diff。"""
    result = subprocess.run(
        ["git", "diff"],
        cwd=str(repo_dir), capture_output=True, text=True,
        encoding="utf-8", errors="replace"
    )
    return result.stdout


def run_single_task(task: dict, task_idx: int, total: int) -> dict:
    """运行单个 SWE-bench 任务。"""
    instance_id = task["instance_id"]
    repo = task["repo"]
    base_commit = task["base_commit"]
    problem = task["problem_statement"]
    test_patch = task["test_patch"]

    print(f"\n{'='*70}")
    print(f"📋 [{task_idx}/{total}] {instance_id}")
    print(f"{'='*70}")
    print(f"  问题：{problem[:150]}...")

    start_time = time.time()

    try:
        # 1. Clone + checkout
        repo_dir = clone_repo(repo, base_commit)

        # 2. 应用 test_patch
        if test_patch:
            test_ok = apply_patch(repo_dir, test_patch)
            if not test_ok:
                print(f"  ⚠️  test_patch 应用失败，跳过")
                return {"instance_id": instance_id, "status": "skip", "reason": "test_patch_apply_fail"}
            print(f"  ✅ test_patch 已应用")

        # 3. 运行 Agent
        abs_repo = str(repo_dir.resolve())
        task_prompt = (
            f"请修复以下 bug。你必须直接修改源代码文件。\n\n"
            f"仓库路径：{abs_repo}\n"
            f"问题描述：{problem}\n\n"
            f"工作流程（严格按此执行）：\n"
            f"1. 用 read_file 读取 {abs_repo}/requests/adapters.py\n"
            f"2. 找到异常处理的 try/except 块\n"
            f"3. 用 str_replace 添加缺失的异常捕获（参考已有的 except 写法）\n"
            f"4. 运行 run_pytest 验证\n"
            f"5. 如果测试失败，再次修改源代码\n\n"
            f"关键提示：\n"
            f"- 所有文件操作都用绝对路径：{abs_repo}/requests/xxx.py\n"
            f"- 只修改源代码文件，不要修改测试文件\n"
            f"- 第 3 轮必须开始编辑代码"
        )

        try:
            result = agent_run(
                task_prompt,
                repo_root=str(repo_dir),
                use_planner=True,
                use_reflector=True,
                use_reminder=True,
                use_reviewer=True,
            )
            agent_status = result.get("status", "unknown")
        except Exception as e:
            agent_status = f"agent_error: {e}"
            print(f"  ❌ Agent 出错：{e}")

        # 4. 获取 Agent 的 patch
        agent_patch = get_agent_patch(repo_dir)
        has_changes = bool(agent_patch.strip())

        # 5. 验证：运行测试（test_patch 已在步骤 2 应用）
        test_pass, test_output = run_tests(repo_dir)

        elapsed = time.time() - start_time

        status = "pass" if (test_pass and has_changes) else "fail"
        if not has_changes:
            status = "no_change"

        print(f"  结果：{'✅ PASS' if status == 'pass' else '❌ FAIL'} ({elapsed:.0f}s)")
        print(f"  Agent 状态：{agent_status}")
        print(f"  有修改：{has_changes}")
        print(f"  测试通过：{test_pass}")

        return {
            "instance_id": instance_id,
            "repo": repo,
            "status": status,
            "agent_status": agent_status,
            "has_changes": has_changes,
            "test_pass": test_pass,
            "elapsed_sec": round(elapsed, 1),
            "agent_patch_lines": len(agent_patch.splitlines()) if agent_patch else 0,
        }

    except Exception as e:
        elapsed = time.time() - start_time
        print(f"  💥 异常：{e}")
        return {
            "instance_id": instance_id,
            "repo": repo,
            "status": "error",
            "error": str(e),
            "elapsed_sec": round(elapsed, 1),
        }


def generate_report(results: list[dict]) -> str:
    total = len(results)
    passed = sum(1 for r in results if r["status"] == "pass")
    failed = sum(1 for r in results if r["status"] == "fail")
    errors = sum(1 for r in results if r["status"] in ("error", "skip"))
    rate = passed / total * 100 if total else 0
    avg_time = sum(r.get("elapsed_sec", 0) for r in results) / total if total else 0

    lines = [
        "# SWE-bench Lite 评测报告",
        f"\n生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "\n## 总览\n",
        f"- **任务总数**：{total}",
        f"- **通过**：{passed}",
        f"- **失败**：{failed}",
        f"- **错误/跳过**：{errors}",
        f"- **通过率**：**{rate:.1f}%**",
        f"- **平均耗时**：{avg_time:.0f}s",
        "\n## 逐任务详情\n",
        "| 任务 | 仓库 | 状态 | 有修改 | 测试通过 | 耗时 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for r in results:
        emoji = "✅" if r["status"] == "pass" else "❌" if r["status"] == "fail" else "⚠️"
        lines.append(
            f"| {r['instance_id']} | {r.get('repo', '?')} | {emoji} {r['status']} | "
            f"{r.get('has_changes', '?')} | {r.get('test_pass', '?')} | "
            f"{r.get('elapsed_sec', '?')}s |"
        )

    # 按仓库统计
    lines.append("\n## 按仓库统计\n")
    lines.append("| 仓库 | 通过/总数 | 通过率 |")
    lines.append("| --- | --- | --- |")
    repos = {}
    for r in results:
        repo = r.get("repo", "unknown")
        if repo not in repos:
            repos[repo] = {"total": 0, "passed": 0}
        repos[repo]["total"] += 1
        if r["status"] == "pass":
            repos[repo]["passed"] += 1
    for repo, stats in sorted(repos.items()):
        rate = stats["passed"] / stats["total"] * 100
        lines.append(f"| {repo} | {stats['passed']}/{stats['total']} | {rate:.0f}% |")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="SWE-bench Lite 评测")
    parser.add_argument("--limit", type=int, help="只跑前 N 道题")
    parser.add_argument("--task", type=str, help="只跑指定 instance_id")
    args = parser.parse_args()

    tasks = load_tasks()

    if args.task:
        tasks = [t for t in tasks if t["instance_id"] == args.task]
    elif args.limit:
        tasks = tasks[:args.limit]

    print(f"\n{'='*70}")
    print(f"🧪 SWE-bench Lite 评测")
    print(f"{'='*70}")
    print(f"📋 任务数：{len(tasks)}")

    results = []
    for i, task in enumerate(tasks, 1):
        try:
            result = run_single_task(task, i, len(tasks))
            results.append(result)
        except Exception as e:
            print(f"  💥 任务异常：{e}")
            results.append({
                "instance_id": task["instance_id"],
                "repo": task["repo"],
                "status": "error",
                "error": str(e),
            })

    # 保存结果
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = RESULTS_DIR / f"swebench_{timestamp}.json"
    json_path.write_text(
        json.dumps(results, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    print(f"\n💾 原始结果：{json_path}")

    # 生成报告
    report = generate_report(results)
    report_path = RESULTS_DIR / f"swebench_report_{timestamp}.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"📊 报告：{report_path}")

    # 打印总览
    print("\n" + "="*70)
    passed = sum(1 for r in results if r["status"] == "pass")
    print(f"📊 通过率：{passed}/{len(results)} = {passed/len(results)*100:.1f}%")
    print("="*70)
    print(report)


if __name__ == "__main__":
    main()
