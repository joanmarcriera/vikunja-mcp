"""Schema for local task YAML files."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class TaskFile(BaseModel):
    id: str
    vikunja_task_id: int
    project_id: int
    title: str
    state: str
    priority: int = 0
    labels: list[str] = Field(default_factory=list)
    assignee: str | None = None
    depends_on: list[str] = Field(default_factory=list)
    source_ref: str | None = None
    repo_path: str | None = None
    branch_name: str | None = None
    objective: str | None = None
    description: str = ""
    acceptance_criteria: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    artifacts: list[str] = Field(default_factory=list)
    updated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

    @classmethod
    def from_path(cls, path: Path) -> TaskFile:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return cls.model_validate(data)

    def to_yaml(self) -> str:
        return yaml.safe_dump(self.model_dump(), sort_keys=False, allow_unicode=False)

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_yaml(), encoding="utf-8")
