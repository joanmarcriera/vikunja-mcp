"""Build Vikunja task filter expressions from ergonomic parameters."""

from __future__ import annotations

from datetime import UTC, datetime

from vikunja_mcp.schemas.tool_io import ListTasksInput


def build_filter_expression(payload: ListTasksInput) -> str | None:
    if payload.filter:
        return payload.filter

    clauses: list[str] = []
    if payload.assigned_to_me:
        clauses.append("assignees.me = true")
    if payload.priority_gte is not None:
        clauses.append(f"priority >= {payload.priority_gte}")
    if payload.completed is not None:
        clauses.append(f"done = {'true' if payload.completed else 'false'}")
    if payload.due_before:
        clauses.append(f'due_date <= "{payload.due_before}"')
    if payload.overdue_only:
        now = datetime.now(UTC).isoformat()
        clauses.append(f'due_date < "{now}"')
        clauses.append("done = false")
    for label in payload.labels:
        clauses.append(f'labels contains "{label}"')

    if not clauses:
        return None
    return " && ".join(clauses)
