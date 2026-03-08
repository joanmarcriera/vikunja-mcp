"""Tool: vikunja_claim_next_task."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from vikunja_mcp.schemas.tool_io import ClaimNextTaskInput
from vikunja_mcp.state_machine import extract_state, replace_state
from vikunja_mcp.tools.common import task_summary
from vikunja_mcp.tools.context import ToolContext
from vikunja_mcp.vikunja_client import VikunjaClient


def _updated_key(value: str | None) -> datetime:
    if not value:
        return datetime.max.replace(tzinfo=UTC)
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def sort_candidates(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        tasks,
        key=lambda item: (
            -int(item.get("priority") or 0),
            _updated_key(item.get("updated") or item.get("updated_at") or item.get("updatedAt")),
            int(item.get("id") or 0),
        ),
    )


def run(ctx: ToolContext, payload: ClaimNextTaskInput) -> dict:
    tasks = ctx.client.list_tasks(project_id=payload.project_id, limit=payload.limit_search)
    candidates: list[dict[str, Any]] = []

    for item in tasks:
        labels = set(VikunjaClient.normalize_labels(item))
        state = extract_state(list(labels)) or "inbox"
        if state != "ready":
            continue
        if payload.accepted_labels and not set(payload.accepted_labels).issubset(labels):
            continue
        if payload.exclude_labels and set(payload.exclude_labels).intersection(labels):
            continue
        if item.get("done"):
            continue
        candidates.append(item)

    ordered = sort_candidates(candidates)
    if payload.priority_order == "asc":
        ordered = list(reversed(ordered))

    for candidate in ordered:
        task_id = int(candidate["id"])
        lock_key = f"claim:{task_id}"
        if not ctx.db.acquire_lock(lock_key, payload.agent_name):
            continue
        try:
            current = ctx.client.get_task(task_id)
            labels = VikunjaClient.normalize_labels(current)
            state = extract_state(labels) or "inbox"
            if state != "ready":
                continue

            new_labels = replace_state(labels, "claimed")
            ctx.client.set_task_labels(task_id, new_labels)

            assignees = set(VikunjaClient.normalize_assignees(current))
            assignees.add(payload.agent_name)
            ctx.client.set_task_assignees(task_id, sorted(assignees))

            note = (
                "### Task Claimed\n"
                f"- actor: `{payload.agent_name}`\n"
                f"- timestamp: `{datetime.now(UTC).isoformat()}`\n"
            )
            ctx.client.add_task_comment(task_id, note)

            task = ctx.client.get_task(task_id)
            return {"claimed": True, "task": task_summary(task)}
        finally:
            ctx.db.release_lock(lock_key)

    return {"claimed": False, "task": None}
