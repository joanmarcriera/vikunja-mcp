"""Tool: vikunja_get_view_tasks."""

from __future__ import annotations

from vikunja_mcp.schemas.tool_io import GetViewTasksInput
from vikunja_mcp.tools.common import task_summary
from vikunja_mcp.tools.context import ToolContext


def _pick_view(views: list[dict], *, view_id: int | None, view_kind: str | None) -> dict:
    if view_id is not None:
        for view in views:
            if int(view.get("id") or 0) == view_id:
                return view
        raise ValueError(f"view_id {view_id} was not found")

    ordered = sorted(views, key=lambda item: float(item.get("position") or 0.0))
    if view_kind:
        for view in ordered:
            if view.get("view_kind") == view_kind:
                return view
        raise ValueError(f"no view found for kind={view_kind}")

    if not ordered:
        raise ValueError("project has no views")
    return ordered[0]


def run(ctx: ToolContext, payload: GetViewTasksInput) -> dict:
    project_id = payload.project_id or ctx.settings.vikunja_default_project_id
    views = ctx.client.list_project_views(project_id)
    selected = _pick_view(views, view_id=payload.view_id, view_kind=payload.view_kind)

    view_id = int(selected["id"])
    view_kind = str(selected.get("view_kind") or "")

    raw_items = ctx.client.list_view_tasks(
        project_id=project_id,
        view_id=view_id,
        limit=payload.limit,
        filter_expression=payload.filter,
        expand=payload.expand,
    )

    if raw_items and isinstance(raw_items[0], dict) and "tasks" in raw_items[0]:
        buckets = []
        for bucket in raw_items:
            tasks = [task_summary(task) for task in bucket.get("tasks", [])]
            buckets.append(
                {
                    "id": int(bucket.get("id") or 0),
                    "title": str(bucket.get("title") or ""),
                    "position": float(bucket.get("position") or 0.0),
                    "task_count": int(bucket.get("count") or len(tasks)),
                    "tasks": tasks,
                }
            )
        return {
            "project_id": project_id,
            "view": {
                "id": view_id,
                "title": selected.get("title"),
                "view_kind": view_kind,
            },
            "mode": "kanban",
            "buckets": buckets,
        }

    tasks = [task_summary(item) for item in raw_items]
    return {
        "project_id": project_id,
        "view": {
            "id": view_id,
            "title": selected.get("title"),
            "view_kind": view_kind,
        },
        "mode": "task_list",
        "tasks": tasks,
        "count": len(tasks),
    }
