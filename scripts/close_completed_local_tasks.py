#!/usr/bin/env python3
"""Archive local task manifests that are complete in Vikunja."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import typer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from vikunja_mcp.config import Settings  # noqa: E402
from vikunja_mcp.main import build_context  # noqa: E402
from vikunja_mcp.schemas.task_file import TaskFile  # noqa: E402
from vikunja_mcp.state_machine import extract_state  # noqa: E402
from vikunja_mcp.vikunja_client import VikunjaClient  # noqa: E402

app = typer.Typer(add_completion=False)


@app.command()
def main() -> None:
    settings = Settings.load()
    ctx, client = build_context(settings)
    moved = 0
    try:
        for path in sorted(settings.tasks_dir.glob("TASK-*.yaml")):
            local = TaskFile.from_path(path)
            remote = ctx.client.get_task(local.vikunja_task_id)
            labels = VikunjaClient.normalize_labels(remote)
            state = extract_state(labels) or "inbox"
            done = bool(remote.get("done")) or state == "done"
            if not done:
                continue
            destination = settings.tasks_done_dir / path.name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(path), str(destination))
            moved += 1
    finally:
        client.close()

    typer.echo(f"Archived {moved} completed task files")


if __name__ == "__main__":
    app()
