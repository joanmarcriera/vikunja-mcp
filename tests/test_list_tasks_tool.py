from __future__ import annotations

from dataclasses import dataclass

from vikunja_mcp.errors import VikunjaValidationError
from vikunja_mcp.schemas.tool_io import ListTasksInput
from vikunja_mcp.tools.list_tasks import run as list_tasks


@dataclass
class FakeSettings:
    vikunja_default_project_id: int = 44
    agent_name: str = "coder.agent"


class FakeClient:
    def __init__(self) -> None:
        self.calls = 0

    def list_tasks(self, *, project_id, filter_expression, limit):
        self.calls += 1
        if filter_expression:
            raise VikunjaValidationError("filter not supported")
        return [
            {
                "id": 1,
                "title": "T1",
                "priority": 2,
                "done": False,
                "project_id": 44,
                "labels": [{"title": "status:ready"}],
                "assignees": [{"username": "coder.agent"}],
            },
            {
                "id": 2,
                "title": "T2",
                "priority": 4,
                "done": False,
                "project_id": 44,
                "labels": [{"title": "status:ready"}, {"title": "agent:coder"}],
                "assignees": [{"username": "coder.agent"}],
            },
        ]


class FakeContext:
    def __init__(self):
        self.settings = FakeSettings()
        self.client = FakeClient()


def test_list_tasks_hybrid_filtering_fallback() -> None:
    ctx = FakeContext()
    payload = ListTasksInput(priority_gte=3, assigned_to_me=True, limit=10)

    result = list_tasks(ctx, payload)

    assert result["filtering_method"] == "hybrid_client_side"
    assert result["count"] == 1
    assert result["tasks"][0]["id"] == 2
    assert ctx.client.calls == 2
