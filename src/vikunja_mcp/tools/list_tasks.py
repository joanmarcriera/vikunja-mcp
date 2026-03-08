"""Tool: vikunja_list_tasks."""

from __future__ import annotations

from datetime import UTC, datetime

from vikunja_mcp.errors import VikunjaValidationError
from vikunja_mcp.filters import build_filter_expression
from vikunja_mcp.schemas.tool_io import ListTasksInput
from vikunja_mcp.tools.common import task_summary
from vikunja_mcp.tools.context import ToolContext


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _apply_client_side_filters(
    tasks: list[dict],
    payload: ListTasksInput,
    *,
    agent_name: str,
) -> list[dict]:
    filtered = tasks

    if payload.labels:
        expected = set(payload.labels)
        filtered = [item for item in filtered if expected.issubset(set(item["labels"]))]

    if payload.priority_gte is not None:
        filtered = [
            item
            for item in filtered
            if int(item.get("priority") or 0) >= payload.priority_gte
        ]

    if payload.completed is not None:
        filtered = [item for item in filtered if item.get("done") is payload.completed]

    due_before_dt = _parse_iso(payload.due_before)
    if due_before_dt:
        filtered = [
            item
            for item in filtered
            if (due := _parse_iso(item.get("due_date"))) is not None and due <= due_before_dt
        ]

    if payload.overdue_only:
        now = datetime.now(UTC)
        filtered = [
            item
            for item in filtered
            if (due := _parse_iso(item.get("due_date"))) is not None
            and due < now
            and not item.get("done")
        ]

    if payload.assigned_to_me:
        filtered = [item for item in filtered if agent_name in set(item.get("assignees", []))]

    return filtered


def run(ctx: ToolContext, payload: ListTasksInput) -> dict:
    project_id = payload.project_id or ctx.settings.vikunja_default_project_id
    expression = build_filter_expression(payload)
    filtering_method = "server_side"

    try:
        tasks = ctx.client.list_tasks(
            project_id=project_id,
            filter_expression=expression,
            limit=payload.limit,
        )
    except VikunjaValidationError:
        if expression is None:
            raise
        tasks = ctx.client.list_tasks(
            project_id=project_id,
            filter_expression=None,
            limit=payload.limit,
        )
        filtering_method = "hybrid_client_side"

    summaries = [task_summary(item) for item in tasks]
    summaries = _apply_client_side_filters(
        summaries,
        payload,
        agent_name=ctx.settings.agent_name,
    )
    summaries = summaries[: payload.limit]

    return {
        "tasks": summaries,
        "count": len(summaries),
        "filtering_method": filtering_method,
    }
