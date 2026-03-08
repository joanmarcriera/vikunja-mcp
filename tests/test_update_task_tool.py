from __future__ import annotations

from vikunja_mcp.schemas.tool_io import UpdateTaskInput
from vikunja_mcp.tools.update_task import run as update_task


class FakeClient:
    def __init__(self):
        self.assignees_calls = 0

    def get_task(self, task_id: int):
        return {
            "id": task_id,
            "labels": [{"title": "status:ready"}],
            "assignees": None,
        }

    def update_task(self, task_id: int, payload: dict):
        return None

    def set_task_labels(self, task_id: int, labels: list[str]):
        return None

    def set_task_assignees(self, task_id: int, assignees: list[str]):
        self.assignees_calls += 1


class FakeContext:
    def __init__(self):
        self.client = FakeClient()


def test_update_task_skips_assignee_sync_without_assignee_changes() -> None:
    ctx = FakeContext()
    payload = UpdateTaskInput(task_id=123, description="noop")

    result = update_task(ctx, payload)

    assert result["updated"] is True
    assert ctx.client.assignees_calls == 0
