"""Tool: vikunja_create_task."""

from __future__ import annotations

from vikunja_mcp.schemas.tool_io import CreateTaskInput
from vikunja_mcp.tools.context import ToolContext


def run(ctx: ToolContext, payload: CreateTaskInput) -> dict:
    if payload.source_ref:
        existing = ctx.db.get_idempotency_task_id(payload.source_ref)
        if existing is None:
            existing = ctx.db.find_task_by_source_ref(payload.source_ref)
        if existing is not None:
            return {"task_id": existing, "created": False, "idempotent_reuse": True}

    create_payload = {
        "title": payload.title,
        "description": payload.description,
        "priority": payload.priority,
        "done": False,
    }
    if payload.due_date is not None:
        create_payload["due_date"] = payload.due_date

    created = ctx.client.create_task(payload.project_id, create_payload)
    task_id = int(created["id"])

    labels = list(dict.fromkeys(payload.labels))
    if labels:
        ctx.client.set_task_labels(task_id, labels)
    if payload.assignees:
        ctx.client.set_task_assignees(task_id, payload.assignees)

    if payload.source_ref:
        ctx.db.set_idempotency_task_id(payload.source_ref, task_id)
        ctx.db.upsert_mapping(f"TASK-{task_id}", task_id, payload.source_ref)

    return {"task_id": task_id, "created": True, "idempotent_reuse": False}
