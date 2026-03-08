from __future__ import annotations

from vikunja_mcp.vikunja_client import VikunjaClient


def test_normalize_labels_and_assignees() -> None:
    task = {
        "labels": [{"title": "status:ready"}, "agent:coder"],
        "assignees": [{"username": "coder.agent"}, "qa.agent"],
    }
    assert VikunjaClient.normalize_labels(task) == ["status:ready", "agent:coder"]
    assert VikunjaClient.normalize_assignees(task) == ["coder.agent", "qa.agent"]


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
