from __future__ import annotations

from vikunja_mcp.vikunja_client import VikunjaClient


def test_normalize_labels_and_assignees() -> None:
    task = {
        "labels": [{"title": "status:ready"}, "agent:coder"],
        "assignees": [{"username": "coder.agent"}, "qa.agent"],
    }
    assert VikunjaClient.normalize_labels(task) == ["status:ready", "agent:coder"]
    assert VikunjaClient.normalize_assignees(task) == ["coder.agent", "qa.agent"]
