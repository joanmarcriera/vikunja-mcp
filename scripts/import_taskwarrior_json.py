#!/usr/bin/env python3
"""Import Taskwarrior-style JSON exports into Vikunja via local tool layer.

Inspired by tw2vikunja-style migration workflows while preserving source_ref idempotency.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import typer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from vikunja_mcp.config import Settings  # noqa: E402
from vikunja_mcp.main import build_context  # noqa: E402
from vikunja_mcp.schemas.tool_io import CreateTaskInput  # noqa: E402
from vikunja_mcp.tools.create_task import run as create_task  # noqa: E402

app = typer.Typer(add_completion=False)


def _map_priority(taskwarrior_priority: str | None) -> int:
    mapping = {"H": 5, "M": 3, "L": 1}
    return mapping.get((taskwarrior_priority or "").upper(), 0)


@app.command()
def main(
    input_json: Path = typer.Argument(..., exists=True),
    project_id: int = typer.Option(..., "--project-id"),
    default_state: str = typer.Option("inbox", "--default-state"),
) -> None:
    settings = Settings.load()
    records = json.loads(input_json.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise typer.BadParameter("input JSON must be a list of task objects")

    created = 0
    reused = 0

    ctx, client = build_context(settings)
    try:
        for row in records:
            if not isinstance(row, dict):
                continue
            title = str(row.get("description") or row.get("title") or "").strip()
            if not title:
                continue

            labels = [f"status:{default_state}"]
            project = row.get("project")
            if isinstance(project, str) and project:
                labels.append(f"tw:project:{project}")
            if row.get("tags") and isinstance(row["tags"], list):
                labels.extend(f"tw:tag:{tag}" for tag in row["tags"] if isinstance(tag, str))

            source_ref = row.get("uuid") or f"tw:line:{created + reused}"
            payload = CreateTaskInput(
                project_id=project_id,
                title=title,
                description=str(row.get("annotation") or ""),
                priority=_map_priority(row.get("priority")),
                due_date=row.get("due"),
                labels=labels,
                source_ref=f"taskwarrior:{source_ref}",
            )
            result = create_task(ctx, payload)
            if result["idempotent_reuse"]:
                reused += 1
            else:
                created += 1
    finally:
        client.close()

    typer.echo({"created": created, "idempotent_reuse": reused})


if __name__ == "__main__":
    app()
