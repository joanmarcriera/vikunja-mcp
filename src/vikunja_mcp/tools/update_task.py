"""Tool: vikunja_update_task."""

from __future__ import annotations

from vikunja_mcp.schemas.tool_io import UpdateTaskInput
from vikunja_mcp.tools.context import ToolContext
from vikunja_mcp.vikunja_client import VikunjaClient


def run(ctx: ToolContext, payload: UpdateTaskInput) -> dict:
    task = ctx.client.get_task(payload.task_id)

    patch: dict[str, object] = {}
    if payload.title is not None:
        patch["title"] = payload.title
    if payload.description is not None:
        patch["description"] = payload.description
    if payload.priority is not None:
        patch["priority"] = payload.priority
    if payload.due_date is not None:
        patch["due_date"] = payload.due_date

    if patch:
        ctx.client.update_task(payload.task_id, patch)

    labels = set(VikunjaClient.normalize_labels(task))
    labels.update(payload.labels_add)
    labels.difference_update(payload.labels_remove)
    ctx.client.set_task_labels(payload.task_id, sorted(labels))

    assignees = set(VikunjaClient.normalize_assignees(task))
    assignees.update(payload.assignees_add)
    assignees.difference_update(payload.assignees_remove)
    ctx.client.set_task_assignees(payload.task_id, sorted(assignees))

    return {"task_id": payload.task_id, "updated": True}
