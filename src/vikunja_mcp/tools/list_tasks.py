"""Tool: vikunja_list_tasks."""

from __future__ import annotations

from vikunja_mcp.filters import build_filter_expression
from vikunja_mcp.schemas.tool_io import ListTasksInput
from vikunja_mcp.tools.common import task_summary
from vikunja_mcp.tools.context import ToolContext


def run(ctx: ToolContext, payload: ListTasksInput) -> dict:
    project_id = payload.project_id or ctx.settings.vikunja_default_project_id
    expression = build_filter_expression(payload)
    tasks = ctx.client.list_tasks(
        project_id=project_id,
        filter_expression=expression,
        limit=payload.limit,
    )

    summaries = [task_summary(item) for item in tasks]
    if payload.labels:
        expected = set(payload.labels)
        summaries = [item for item in summaries if expected.issubset(set(item["labels"]))]

    if payload.overdue_only:
        summaries = [item for item in summaries if item.get("due_date") and not item.get("done")]

    if payload.completed is not None:
        summaries = [item for item in summaries if item.get("done") is payload.completed]

    summaries = summaries[: payload.limit]
    return {"tasks": summaries, "count": len(summaries)}
