from __future__ import annotations

from vikunja_mcp.tools.claim_next_task import sort_candidates


def test_claim_ordering_priority_then_age_then_id() -> None:
    tasks = [
        {"id": 10, "priority": 2, "updated": "2026-03-08T10:00:00+00:00"},
        {"id": 9, "priority": 3, "updated": "2026-03-08T12:00:00+00:00"},
        {"id": 7, "priority": 3, "updated": "2026-03-08T11:00:00+00:00"},
        {"id": 8, "priority": 3, "updated": "2026-03-08T11:00:00+00:00"},
    ]

    ordered = sort_candidates(tasks)
    ordered_ids = [item["id"] for item in ordered]
    assert ordered_ids == [7, 8, 9, 10]
