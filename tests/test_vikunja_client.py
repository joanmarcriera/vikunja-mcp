from __future__ import annotations

from vikunja_mcp.errors import VikunjaValidationError
from vikunja_mcp.vikunja_client import VikunjaClient


def test_normalize_labels_and_assignees() -> None:
    task = {
        "labels": [{"title": "status:ready"}, "agent:coder"],
        "assignees": [{"username": "coder.agent"}, "qa.agent"],
    }
    assert VikunjaClient.normalize_labels(task) == ["status:ready", "agent:coder"]
    assert VikunjaClient.normalize_assignees(task) == ["coder.agent", "qa.agent"]


def test_normalize_handles_null_collections() -> None:
    task = {"labels": None, "assignees": None}
    assert VikunjaClient.normalize_labels(task) == []
    assert VikunjaClient.normalize_assignees(task) == []


def test_list_tasks_paginates_with_limits() -> None:
    client = VikunjaClient(
        "https://example.test/api/v1",
        "token",
        verify_ssl=False,
        max_page_size=2,
        max_fetch_tasks=10,
    )

    def fake_request(method, path, **kwargs):
        page = kwargs["params"]["page"]
        if page == 1:
            return [{"id": 1}, {"id": 2}]
        if page == 2:
            return [{"id": 3}, {"id": 4}]
        return []

    client._request = fake_request  # type: ignore[method-assign]
    tasks = client.list_tasks(limit=3)

    assert [task["id"] for task in tasks] == [1, 2, 3]
    client.close()


def test_list_tasks_falls_back_to_project_endpoint() -> None:
    client = VikunjaClient(
        "https://example.test/api/v1",
        "token",
        verify_ssl=False,
        max_page_size=2,
        max_fetch_tasks=10,
    )

    calls: list[str] = []

    def fake_request(method, path, **kwargs):
        calls.append(path)
        if path == "/projects/44/tasks":
            return [{"id": 10}]
        if path == "/tasks/all":
            raise VikunjaValidationError("Invalid model provided: Bad Request")
        return []

    client._request = fake_request  # type: ignore[method-assign]
    tasks = client.list_tasks(project_id=44, limit=5)

    assert [task["id"] for task in tasks] == [10]
    assert calls[0] == "/projects/44/tasks"
    client.close()
