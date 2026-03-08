"""Tool: vikunja_move_task_to_bucket."""

from __future__ import annotations

from vikunja_mcp.schemas.tool_io import MoveTaskToBucketInput
from vikunja_mcp.tools.context import ToolContext


def _resolve_kanban_view_id(views: list[dict], explicit_view_id: int | None) -> int:
    if explicit_view_id is not None:
        return explicit_view_id
    ordered = sorted(views, key=lambda item: float(item.get("position") or 0.0))
    for view in ordered:
        if view.get("view_kind") == "kanban":
            return int(view.get("id") or 0)
    raise ValueError("no kanban view found on this project")


def _resolve_bucket_id(
    buckets: list[dict],
    explicit_bucket_id: int | None,
    bucket_title: str | None,
) -> int:
    if explicit_bucket_id is not None:
        return explicit_bucket_id
    if not bucket_title:
        raise ValueError("provide either bucket_id or bucket_title")

    wanted = bucket_title.casefold()
    for bucket in buckets:
        title = str(bucket.get("title") or "")
        if title.casefold() == wanted:
            return int(bucket.get("id") or 0)
    raise ValueError(f"bucket not found: {bucket_title}")


def run(ctx: ToolContext, payload: MoveTaskToBucketInput) -> dict:
    project_id = payload.project_id or ctx.settings.vikunja_default_project_id
    views = ctx.client.list_project_views(project_id)
    view_id = _resolve_kanban_view_id(views, payload.view_id)

    buckets = ctx.client.list_view_buckets(project_id, view_id)
    bucket_id = _resolve_bucket_id(buckets, payload.bucket_id, payload.bucket_title)

    moved = ctx.client.move_task_to_bucket(
        project_id=project_id,
        view_id=view_id,
        bucket_id=bucket_id,
        task_id=payload.task_id,
    )

    selected_bucket = next(
        (bucket for bucket in buckets if int(bucket.get("id") or 0) == bucket_id),
        {},
    )

    return {
        "project_id": project_id,
        "view_id": view_id,
        "task_id": payload.task_id,
        "bucket_id": bucket_id,
        "bucket_title": selected_bucket.get("title"),
        "moved": True,
        "task_bucket": moved,
    }
