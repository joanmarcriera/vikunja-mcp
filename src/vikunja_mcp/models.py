"""Shared data models for tasks and sync operations."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class TaskSummary(BaseModel):
    id: int
    title: str
    description: str = ""
    done: bool = False
    priority: int = 0
    due_date: str | None = None
    project_id: int
    labels: list[str] = Field(default_factory=list)
    assignees: list[str] = Field(default_factory=list)
    updated: str | None = None


class TaskDetail(TaskSummary):
    comments: list[dict[str, Any]] = Field(default_factory=list)
    attachments: list[dict[str, Any]] = Field(default_factory=list)
    related_tasks: list[dict[str, Any]] = Field(default_factory=list)
    created: str | None = None


class SyncConflict(BaseModel):
    local_file: str
    task_id: int
    reason: str


class SyncResult(BaseModel):
    created_in_vikunja: int = 0
    updated_in_vikunja: int = 0
    created_locally: int = 0
    archived_locally: int = 0
    conflicts: list[SyncConflict] = Field(default_factory=list)


class ExecutionNote(BaseModel):
    task_id: int
    actor: str
    note_type: str
    content: str
    append_artifact_paths: list[str] = Field(default_factory=list)

    def to_markdown(self) -> str:
        lines = [
            "### Execution Note",
            f"- actor: `{self.actor}`",
            f"- timestamp: `{datetime.now(UTC).isoformat()}`",
            f"- note_type: `{self.note_type}`",
            "",
            self.content.strip(),
        ]
        if self.append_artifact_paths:
            lines.append("")
            lines.append("Artifacts:")
            lines.extend(f"- `{item}`" for item in self.append_artifact_paths)
        return "\n".join(lines)
