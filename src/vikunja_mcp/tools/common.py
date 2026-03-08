"""Common task normalization helpers for tool outputs."""

from __future__ import annotations

from typing import Any

from vikunja_mcp.vikunja_client import VikunjaClient


def task_summary(task: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": int(task.get("id", 0)),
        "title": str(task.get("title") or ""),
        "description": str(task.get("description") or ""),
        "done": bool(task.get("done", False)),
        "priority": int(task.get("priority") or 0),
        "due_date": task.get("due_date") or task.get("dueDate"),
        "project_id": int(task.get("project_id") or task.get("projectId") or 0),
        "labels": VikunjaClient.normalize_labels(task),
        "assignees": VikunjaClient.normalize_assignees(task),
        "updated": task.get("updated") or task.get("updated_at") or task.get("updatedAt"),
    }


def task_detail(
    task: dict[str, Any],
    comments: list[dict],
    attachments: list[dict],
) -> dict[str, Any]:
    result = task_summary(task)
    result.update(
        {
            "comments": comments,
            "attachments": attachments,
            "related_tasks": task.get("related_tasks", []),
            "created": task.get("created") or task.get("created_at") or task.get("createdAt"),
        }
    )
    return result
