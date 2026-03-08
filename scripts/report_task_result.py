#!/usr/bin/env python3
"""Report execution result back to Vikunja and move task state."""

from __future__ import annotations

import sys
from pathlib import Path

import typer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from vikunja_mcp.config import Settings  # noqa: E402
from vikunja_mcp.main import build_context  # noqa: E402
from vikunja_mcp.schemas.task_file import TaskFile  # noqa: E402
from vikunja_mcp.schemas.tool_io import AddExecutionNoteInput, TransitionTaskInput  # noqa: E402
from vikunja_mcp.state_machine import replace_state  # noqa: E402
from vikunja_mcp.tools.add_execution_note import run as add_execution_note  # noqa: E402
from vikunja_mcp.tools.transition_task import run as transition_task  # noqa: E402

app = typer.Typer(add_completion=False)


@app.command()
def main(
    task_file: Path = typer.Argument(..., exists=True),
    result: str = typer.Option(
        ..., "--result", help="success | blocked | retryable_failure | unrecoverable"
    ),
    note_file: Path | None = typer.Option(None, "--note-file", exists=True),
) -> None:
    settings = Settings.load()
    task = TaskFile.from_path(task_file)

    outputs_dir = settings.outputs_dir / f"task-{task.vikunja_task_id}"
    summary_path = outputs_dir / "summary.md"
    note_content = ""
    if note_file:
        note_content = note_file.read_text(encoding="utf-8")
    elif summary_path.exists():
        note_content = summary_path.read_text(encoding="utf-8")
    else:
        note_content = f"Execution finished with result: {result}."

    artifacts = [str(p) for p in sorted(outputs_dir.glob("*")) if p.is_file()]

    transition_map = {
        "success": "review",
        "blocked": "blocked",
        "retryable_failure": "in_progress",
        "unrecoverable": "ready",
    }
    if result not in transition_map:
        raise typer.BadParameter(
            "result must be one of success|blocked|retryable_failure|unrecoverable"
        )

    ctx, client = build_context(settings)
    try:
        add_execution_note(
            ctx,
            AddExecutionNoteInput(
                task_id=task.vikunja_task_id,
                actor=task.assignee or settings.agent_name,
                note_type=result,
                content=note_content,
                append_artifact_paths=artifacts,
            ),
        )

        target_state = transition_map[result]
        if task.state != target_state:
            transition_task(
                ctx,
                TransitionTaskInput(
                    task_id=task.vikunja_task_id,
                    to_state=target_state,
                    actor=task.assignee or settings.agent_name,
                    reason=f"Task result reported: {result}",
                    force=(result == "retryable_failure"),
                ),
            )
        task.state = target_state
        task.labels = replace_state(task.labels, target_state)
        task.artifacts = artifacts
        task.write(task_file)
    finally:
        client.close()

    typer.echo(f"Reported {result} for {task.id}")


if __name__ == "__main__":
    app()
