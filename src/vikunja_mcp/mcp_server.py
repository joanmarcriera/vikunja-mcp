"""MCP server registration for Vikunja tools."""

from __future__ import annotations

from vikunja_mcp.schemas.tool_io import (
    AddExecutionNoteInput,
    ClaimNextTaskInput,
    CreateTaskInput,
    GetTaskInput,
    ListTasksInput,
    SyncFsTasksInput,
    TransitionTaskInput,
    UpdateTaskInput,
)
from vikunja_mcp.tools import (
    add_execution_note,
    claim_next_task,
    create_task,
    get_task,
    list_tasks,
    sync_fs_tasks,
    transition_task,
    update_task,
)
from vikunja_mcp.tools.context import ToolContext


def create_mcp_server(ctx: ToolContext):
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "MCP SDK is not installed. Install dependency `mcp` to run the server."
        ) from exc

    mcp = FastMCP("vikunja-mcp-server")

    @mcp.tool(
        name="vikunja_list_tasks",
        description=(
            "List tasks with agent-friendly filters. Read-only operation. Use before planning "
            "or when selecting work candidates."
        ),
    )
    def vikunja_list_tasks(input_data: ListTasksInput) -> dict:
        return list_tasks(ctx, input_data)

    @mcp.tool(
        name="vikunja_get_task",
        description=(
            "Fetch one task with full details including comments. Read-only operation. "
            "Use before mutating state."
        ),
    )
    def vikunja_get_task(input_data: GetTaskInput) -> dict:
        return get_task(ctx, input_data)

    @mcp.tool(
        name="vikunja_create_task",
        description=(
            "Create a structured task and optionally enforce idempotency with source_ref. "
            "Mutates remote state."
        ),
    )
    def vikunja_create_task(input_data: CreateTaskInput) -> dict:
        return create_task(ctx, input_data)

    @mcp.tool(
        name="vikunja_update_task",
        description=(
            "Update bounded mutable fields (title/description/priority/due_date/labels/assignees). "
            "Mutates remote state."
        ),
    )
    def vikunja_update_task(input_data: UpdateTaskInput) -> dict:
        return update_task(ctx, input_data)

    @mcp.tool(
        name="vikunja_transition_task",
        description=(
            "Apply validated state transition using status:* labels. Expects workflow discipline "
            "(ready->claimed->in_progress->review->done). Mutates remote state."
        ),
    )
    def vikunja_transition_task(input_data: TransitionTaskInput) -> dict:
        return transition_task(ctx, input_data)

    @mcp.tool(
        name="vikunja_claim_next_task",
        description=(
            "Atomically claim next eligible ready task for an agent using deterministic ordering. "
            "Mutates remote state and local lock metadata."
        ),
    )
    def vikunja_claim_next_task(input_data: ClaimNextTaskInput) -> dict:
        return claim_next_task(ctx, input_data)

    @mcp.tool(
        name="vikunja_add_execution_note",
        description=(
            "Append structured execution note to a task comment stream for audit trail. "
            "Mutates remote state."
        ),
    )
    def vikunja_add_execution_note(input_data: AddExecutionNoteInput) -> dict:
        return add_execution_note(ctx, input_data)

    @mcp.tool(
        name="vikunja_sync_fs_tasks",
        description=(
            "Synchronize local tasks/ YAML manifests with Vikunja tasks. Supports dry-run and "
            "conflict reporting. Mutates local and/or remote state."
        ),
    )
    def vikunja_sync_fs_tasks(input_data: SyncFsTasksInput) -> dict:
        return sync_fs_tasks(ctx, input_data)

    return mcp
