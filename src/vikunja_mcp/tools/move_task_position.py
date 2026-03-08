"""Tool: vikunja_move_task_position."""

from __future__ import annotations

from vikunja_mcp.schemas.tool_io import MoveTaskPositionInput
from vikunja_mcp.tools.context import ToolContext


def run(ctx: ToolContext, payload: MoveTaskPositionInput) -> dict:
    result = ctx.client.update_task_position(
        task_id=payload.task_id,
        project_view_id=payload.project_view_id,
        position=payload.position,
    )
    return {
        "task_id": payload.task_id,
        "project_view_id": payload.project_view_id,
        "position": payload.position,
        "updated": True,
        "task_position": result,
    }
