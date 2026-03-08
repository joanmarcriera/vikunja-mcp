#!/usr/bin/env python3
"""Build a prompt packet from task YAML and run a placeholder Aider command."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import typer
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from vikunja_mcp.config import Settings  # noqa: E402
from vikunja_mcp.schemas.task_file import TaskFile  # noqa: E402

app = typer.Typer(add_completion=False)


@app.command()
def main(
    task_file: Path = typer.Argument(..., exists=True),
    command: str = typer.Option(
        "",
        "--command",
        help=(
            "Placeholder command for Claude Code Router / Aider. "
            "Defaults to AIDER_COMMAND env or echo."
        ),
    ),
) -> None:
    settings = Settings.load()
    task = TaskFile.from_path(task_file)

    out_dir = settings.outputs_dir / f"task-{task.vikunja_task_id}"
    out_dir.mkdir(parents=True, exist_ok=True)

    prompt_packet = {
        "task_id": task.id,
        "vikunja_task_id": task.vikunja_task_id,
        "role": task.assignee or settings.agent_name,
        "repo_path": task.repo_path or str(ROOT),
        "branch_name": task.branch_name or f"task-{task.vikunja_task_id}",
        "objective": task.objective or task.title,
        "description": task.description,
        "acceptance_criteria": task.acceptance_criteria,
        "constraints": task.constraints,
        "deliverables": ["code changes", "tests", "summary.md"],
    }

    packet_yaml = out_dir / "prompt_packet.yaml"
    packet_json = out_dir / "prompt_packet.json"
    packet_yaml.write_text(yaml.safe_dump(prompt_packet, sort_keys=False), encoding="utf-8")
    packet_json.write_text(json.dumps(prompt_packet, indent=2), encoding="utf-8")

    run_command = command or os.getenv("AIDER_COMMAND") or "echo '[placeholder] run aider here'"
    completed = subprocess.run(
        run_command,
        shell=True,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    (out_dir / "run.log").write_text(
        "\n".join(
            [
                f"command: {run_command}",
                f"exit_code: {completed.returncode}",
                "--- stdout ---",
                completed.stdout,
                "--- stderr ---",
                completed.stderr,
            ]
        ),
        encoding="utf-8",
    )

    summary = out_dir / "summary.md"
    if not summary.exists():
        summary.write_text(
            "# Task Execution Summary\n\n"
            f"Task: {task.id}\n\n"
            f"Command: `{run_command}`\n\n"
            f"Exit code: {completed.returncode}\n",
            encoding="utf-8",
        )

    typer.echo(f"Prompt packet: {packet_yaml}")
    typer.echo(f"Run log: {out_dir / 'run.log'}")


if __name__ == "__main__":
    app()
