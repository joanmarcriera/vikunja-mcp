"""Tool: vikunja_get_task."""

from __future__ import annotations

from vikunja_mcp.schemas.tool_io import GetTaskInput
from vikunja_mcp.tools.common import task_detail
from vikunja_mcp.tools.context import ToolContext


def run(ctx: ToolContext, payload: GetTaskInput) -> dict:
    task = ctx.client.get_task(payload.task_id)
    comments = ctx.client.get_task_comments(payload.task_id)
    attachments = task.get("attachments", [])
    return {"task": task_detail(task, comments, attachments)}
