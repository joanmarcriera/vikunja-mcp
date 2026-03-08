from __future__ import annotations

from dataclasses import dataclass

from vikunja_mcp.schemas.tool_io import GetViewTasksInput, MoveTaskToBucketInput
from vikunja_mcp.tools.get_view_tasks import run as get_view_tasks
from vikunja_mcp.tools.move_task_to_bucket import run as move_task_to_bucket


@dataclass
class FakeSettings:
    vikunja_default_project_id: int = 44


class FakeClient:
    def list_project_views(self, project_id: int):
        return [
            {"id": 1, "title": "Table", "view_kind": "table", "position": 1},
            {"id": 2, "title": "Kanban", "view_kind": "kanban", "position": 2},
        ]

    def list_view_tasks(
        self,
        *,
        project_id: int,
        view_id: int,
        limit: int,
        filter_expression,
        expand,
    ):
        assert project_id == 44
        assert view_id == 2
        return [
            {
                "id": 10,
                "title": "To-Do",
                "position": 1,
                "count": 1,
                "tasks": [
                    {
                        "id": 123,
                        "title": "Ship feature",
                        "project_id": 44,
                        "labels": [{"title": "status:ready"}],
                        "assignees": [],
                        "priority": 3,
                        "done": False,
                    }
                ],
            }
        ]

    def list_view_buckets(self, project_id: int, view_id: int):
        return [{"id": 10, "title": "To-Do"}, {"id": 11, "title": "Doing"}]

    def move_task_to_bucket(self, *, project_id: int, view_id: int, bucket_id: int, task_id: int):
        return {
            "project_view_id": view_id,
            "bucket_id": bucket_id,
            "task_id": task_id,
        }


class FakeContext:
    def __init__(self) -> None:
        self.settings = FakeSettings()
        self.client = FakeClient()


def test_get_view_tasks_returns_kanban_mode() -> None:
    ctx = FakeContext()
    payload = GetViewTasksInput(project_id=44, view_kind="kanban", limit=20)

    result = get_view_tasks(ctx, payload)

    assert result["mode"] == "kanban"
    assert result["view"]["id"] == 2
    assert result["buckets"][0]["tasks"][0]["id"] == 123


def test_move_task_to_bucket_resolves_by_title() -> None:
    ctx = FakeContext()
    payload = MoveTaskToBucketInput(
        project_id=44,
        view_id=2,
        task_id=123,
        bucket_title="Doing",
    )

    result = move_task_to_bucket(ctx, payload)

    assert result["moved"] is True
    assert result["bucket_id"] == 11
