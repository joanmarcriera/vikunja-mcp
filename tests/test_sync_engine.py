from __future__ import annotations

from pathlib import Path

from vikunja_mcp.db import LocalDB
from vikunja_mcp.sync_engine import SyncEngine


class DummyClient:
    def list_tasks(self, **kwargs):
        return []


def test_sync_conflict_detection(tmp_path: Path) -> None:
    db = LocalDB(tmp_path / "state.db")
    engine = SyncEngine(
        client=DummyClient(),
        db=db,
        tasks_dir=tmp_path / "tasks",
        tasks_done_dir=tmp_path / "tasks_done",
    )

    task_id = 123
    db.upsert_sync_meta(
        task_id=task_id,
        local_file=str(tmp_path / "tasks/TASK-123.yaml"),
        local_checksum="old-local",
        remote_updated="2026-03-08T10:00:00+00:00",
    )

    assert engine._sync_meta_conflict(
        task_id=task_id,
        local_checksum="new-local",
        remote_updated="2026-03-08T11:00:00+00:00",
    )

    assert not engine._sync_meta_conflict(
        task_id=task_id,
        local_checksum="new-local",
        remote_updated="2026-03-08T10:00:00+00:00",
    )
