"""Tool: vikunja_add_execution_note."""

from __future__ import annotations

from vikunja_mcp.models import ExecutionNote
from vikunja_mcp.schemas.tool_io import AddExecutionNoteInput
from vikunja_mcp.tools.context import ToolContext


def run(ctx: ToolContext, payload: AddExecutionNoteInput) -> dict:
    note = ExecutionNote(
        task_id=payload.task_id,
        actor=payload.actor,
        note_type=payload.note_type,
        content=payload.content,
        append_artifact_paths=payload.append_artifact_paths,
    )
    ctx.client.add_task_comment(payload.task_id, note.to_markdown())
    return {"task_id": payload.task_id, "comment_added": True}
