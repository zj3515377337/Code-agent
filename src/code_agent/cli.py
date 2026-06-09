import os
from pathlib import Path
import typer
from dotenv import load_dotenv
from code_agent.actor import run

load_dotenv(Path(__file__).parent.parent.parent / ".env")

app = typer.Typer(help="Code Agent - 让 AI 帮你写代码")


@app.command()
def main(
    task: str = typer.Argument(..., help="你想让 Agent 完成的任务"),
    repo_root: str = typer.Option(".", help="项目根目录"),
    model: str = typer.Option(None, help="LLM 模型名，默认读环境变量或 deepseek-chat"),
    log_file: str = typer.Option(None, help="日志文件路径，默认 logs/agent.log"),
    no_planner: bool = typer.Option(False, help="[消融] 关闭规划模块"),
    no_reflector: bool = typer.Option(False, help="[消融] 关闭反思模块"),
    no_reminder: bool = typer.Option(False, help="[消融] 关闭行为约束模块"),
    no_reviewer: bool = typer.Option(False, help="[消融] 关闭审查模块"),
):
    if model:
        os.environ["AGENT_MODEL"] = model
    if log_file:
        os.environ["AGENT_LOG_FILE"] = log_file
    run(
        task,
        repo_root=repo_root,
        use_planner=not no_planner,
        use_reflector=not no_reflector,
        use_reminder=not no_reminder,
        use_reviewer=not no_reviewer,
    )


if __name__ == "__main__":
    app()
