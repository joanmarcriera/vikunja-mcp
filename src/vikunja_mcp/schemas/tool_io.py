"""Tool I/O schema definitions."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ListTasksInput(BaseModel):
    project_id: int | None = None
    filter: str | None = None
    assigned_to_me: bool | None = None
    labels: list[str] = Field(default_factory=list)
    priority_gte: int | None = None
    due_before: str | None = None
    overdue_only: bool | None = None
    completed: bool | None = None
    limit: int = 50


class GetTaskInput(BaseModel):
    task_id: int


class CreateTaskInput(BaseModel):
    project_id: int
    title: str
    description: str = ""
    priority: int = 0
    due_date: str | None = None
    labels: list[str] = Field(default_factory=list)
    assignees: list[str] = Field(default_factory=list)
    source_ref: str | None = None


class UpdateTaskInput(BaseModel):
    task_id: int
    title: str | None = None
    description: str | None = None
    priority: int | None = None
    due_date: str | None = None
    labels_add: list[str] = Field(default_factory=list)
    labels_remove: list[str] = Field(default_factory=list)
    assignees_add: list[str] = Field(default_factory=list)
    assignees_remove: list[str] = Field(default_factory=list)


class TransitionTaskInput(BaseModel):
    task_id: int
    to_state: str
    actor: str
    reason: str
    expected_from_state: str | None = None
    force: bool = False


class ClaimNextTaskInput(BaseModel):
    project_id: int
    agent_name: str
    accepted_labels: list[str] = Field(default_factory=list)
    exclude_labels: list[str] = Field(default_factory=list)
    priority_order: str = "desc"
    limit_search: int = 20


class AddExecutionNoteInput(BaseModel):
    task_id: int
    actor: str
    note_type: str
    content: str
    append_artifact_paths: list[str] = Field(default_factory=list)


class SyncFsTasksInput(BaseModel):
    direction: str = "bidirectional"
    tasks_dir: str | None = None
    archive_dir: str | None = None
    project_id: int
    dry_run: bool = False
