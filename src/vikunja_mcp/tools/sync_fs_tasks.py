"""Tool: vikunja_sync_fs_tasks."""

from __future__ import annotations

from pathlib import Path

from vikunja_mcp.schemas.tool_io import SyncFsTasksInput
from vikunja_mcp.tools.context import ToolContext


def run(ctx: ToolContext, payload: SyncFsTasksInput) -> dict:
    tasks_dir = Path(payload.tasks_dir) if payload.tasks_dir else None
    archive_dir = Path(payload.archive_dir) if payload.archive_dir else None

    result = ctx.sync_engine.sync(
        direction=payload.direction,
        project_id=payload.project_id,
        dry_run=payload.dry_run,
        tasks_dir=tasks_dir,
        archive_dir=archive_dir,
    )
    return result.model_dump()
