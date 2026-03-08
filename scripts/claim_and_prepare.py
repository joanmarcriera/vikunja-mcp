#!/usr/bin/env python3
"""Claim next eligible task and prepare local manifest + outputs folder."""

from __future__ import annotations

import sys
from pathlib import Path

import typer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from vikunja_mcp.config import Settings  # noqa: E402
from vikunja_mcp.main import build_context  # noqa: E402
from vikunja_mcp.schemas.task_file import TaskFile  # noqa: E402
from vikunja_mcp.schemas.tool_io import ClaimNextTaskInput, GetTaskInput  # noqa: E402
from vikunja_mcp.tools.claim_next_task import run as claim_next_task  # noqa: E402
from vikunja_mcp.tools.get_task import run as get_task  # noqa: E402

app = typer.Typer(add_completion=False)


@app.command()
def main(
    project_id: int = typer.Option(..., "--project-id"),
    agent: str = typer.Option(..., "--agent"),
    accepted_label: list[str] = typer.Option([], "--accepted-label"),
    exclude_label: list[str] = typer.Option([], "--exclude-label"),
) -> None:
    settings = Settings.load()
    ctx, client = build_context(settings)
    try:
        claim = claim_next_task(
            ctx,
            ClaimNextTaskInput(
                project_id=project_id,
                agent_name=agent,
                accepted_labels=accepted_label,
                exclude_labels=exclude_label,
            ),
        )
        if not claim["claimed"]:
            typer.echo("No eligible task claimed")
            raise typer.Exit(code=0)

        task_id = int(claim["task"]["id"])
        detail = get_task(ctx, GetTaskInput(task_id=task_id))["task"]

        state = "claimed"
        labels = detail.get("labels", [])
        output_dir = settings.outputs_dir / f"task-{task_id}"
        output_dir.mkdir(parents=True, exist_ok=True)

        task_file = TaskFile(
            id=f"TASK-{task_id}",
            vikunja_task_id=task_id,
            project_id=detail["project_id"],
            title=detail["title"],
            state=state,
            priority=detail.get("priority", 0),
            labels=labels,
            assignee=agent,
            objective=detail["title"],
            description=detail.get("description", ""),
            artifacts=[str(output_dir / "summary.md")],
            updated_at=detail.get("updated") or "",
        )

        task_path = settings.tasks_dir / f"TASK-{task_id}.yaml"
        task_file.write(task_path)

        typer.echo(f"Claimed task {task_id}")
        typer.echo(f"Task file: {task_path}")
        typer.echo(f"Outputs dir: {output_dir}")
    finally:
        client.close()


if __name__ == "__main__":
    app()
