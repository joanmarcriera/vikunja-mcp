from __future__ import annotations

from pathlib import Path

from vikunja_mcp.db import LocalDB
from vikunja_mcp.schemas.tool_io import CreateTaskInput
from vikunja_mcp.tools.context import ToolContext
from vikunja_mcp.tools.create_task import run as create_task


class FakeClient:
    def __init__(self):
        self.created = 0

    def create_task(self, project_id, payload):
        self.created += 1
        return {"id": 900 + self.created}

    def set_task_labels(self, task_id, labels):
        return None

    def set_task_assignees(self, task_id, assignees):
        return None


class FakeSyncEngine:
    pass


class FakeSettings:
    pass


def test_create_task_idempotency(tmp_path: Path) -> None:
    db = LocalDB(tmp_path / "test.db")
    client = FakeClient()
    ctx = ToolContext(settings=FakeSettings(), client=client, db=db, sync_engine=FakeSyncEngine())

    payload = CreateTaskInput(
        project_id=44,
        title="Implement auth middleware",
        source_ref="repo:epic-44:story-123",
    )

    first = create_task(ctx, payload)
    second = create_task(ctx, payload)

    assert first["created"] is True
    assert second["idempotent_reuse"] is True
    assert client.created == 1
