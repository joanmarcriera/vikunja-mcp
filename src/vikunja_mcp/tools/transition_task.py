"""Tool: vikunja_transition_task."""

from __future__ import annotations

from vikunja_mcp.schemas.tool_io import TransitionTaskInput
from vikunja_mcp.state_machine import extract_state, replace_state, validate_transition
from vikunja_mcp.tools.context import ToolContext
from vikunja_mcp.vikunja_client import VikunjaClient


def run(ctx: ToolContext, payload: TransitionTaskInput) -> dict:
    task = ctx.client.get_task(payload.task_id)
    labels = VikunjaClient.normalize_labels(task)

    current_state = extract_state(labels) or "inbox"
    if payload.expected_from_state and payload.expected_from_state != current_state:
        raise ValueError(
            "expected_from_state mismatch: "
            f"expected={payload.expected_from_state} actual={current_state}"
        )

    validate_transition(current_state, payload.to_state, force=payload.force)

    new_labels = replace_state(labels, payload.to_state)
    ctx.client.set_task_labels(payload.task_id, new_labels)

    if payload.to_state == "done":
        ctx.client.update_task(payload.task_id, {"done": True})
    elif task.get("done"):
        ctx.client.update_task(payload.task_id, {"done": False})

    note = (
        "### State Transition\n"
        f"- actor: `{payload.actor}`\n"
        f"- from_state: `{current_state}`\n"
        f"- to_state: `{payload.to_state}`\n"
        f"- reason: {payload.reason}\n"
    )
    ctx.client.add_task_comment(payload.task_id, note)

    return {
        "task_id": payload.task_id,
        "from_state": current_state,
        "to_state": payload.to_state,
        "updated": True,
    }
