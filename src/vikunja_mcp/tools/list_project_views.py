"""Tool: vikunja_list_project_views."""

from __future__ import annotations

from vikunja_mcp.schemas.tool_io import ListProjectViewsInput
from vikunja_mcp.tools.context import ToolContext


def run(ctx: ToolContext, payload: ListProjectViewsInput) -> dict:
    project_id = payload.project_id or ctx.settings.vikunja_default_project_id
    views = ctx.client.list_project_views(project_id)

    if payload.view_kind:
        views = [view for view in views if view.get("view_kind") == payload.view_kind]

    views = sorted(views, key=lambda item: float(item.get("position") or 0.0))
    result = [
        {
            "id": int(view.get("id") or 0),
            "project_id": int(view.get("project_id") or project_id),
            "title": str(view.get("title") or ""),
            "view_kind": str(view.get("view_kind") or ""),
            "position": float(view.get("position") or 0.0),
            "default_bucket_id": view.get("default_bucket_id"),
            "done_bucket_id": view.get("done_bucket_id"),
        }
        for view in views
    ]

    return {"project_id": project_id, "views": result, "count": len(result)}
