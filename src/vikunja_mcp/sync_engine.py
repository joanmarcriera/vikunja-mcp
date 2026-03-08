"""Synchronize local task YAML files with Vikunja tasks."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from vikunja_mcp.db import LocalDB
from vikunja_mcp.models import SyncConflict, SyncResult
from vikunja_mcp.schemas.task_file import TaskFile
from vikunja_mcp.state_machine import extract_state
from vikunja_mcp.vikunja_client import VikunjaClient


class SyncEngine:
    def __init__(
        self,
        *,
        client: VikunjaClient,
        db: LocalDB,
        tasks_dir: Path,
        tasks_done_dir: Path,
    ):
        self.client = client
        self.db = db
        self.tasks_dir = tasks_dir
        self.tasks_done_dir = tasks_done_dir

    @staticmethod
    def _checksum(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    @staticmethod
    def _remote_updated(task: dict[str, Any]) -> str | None:
        for key in ("updated", "updated_at", "updatedAt"):
            value = task.get(key)
            if isinstance(value, str):
                return value
        return None

    def _task_file_path(self, task_id: int) -> Path:
        return self.tasks_dir / f"TASK-{task_id}.yaml"

    def _task_from_remote(self, remote: dict[str, Any], project_id: int) -> TaskFile:
        task_id = int(remote["id"])
        labels = self.client.normalize_labels(remote)
        state = extract_state(labels) or "inbox"
        assignees = self.client.normalize_assignees(remote)
        return TaskFile(
            id=f"TASK-{task_id}",
            vikunja_task_id=task_id,
            project_id=int(remote.get("project_id") or project_id),
            title=str(remote.get("title", "")),
            state=state,
            priority=int(remote.get("priority") or 0),
            labels=labels,
            assignee=assignees[0] if assignees else None,
            description=str(remote.get("description") or ""),
            updated_at=self._remote_updated(remote) or "",
            objective=str(remote.get("title") or ""),
        )

    def _apply_local_to_remote(self, local: TaskFile, remote: dict[str, Any]) -> None:
        payload: dict[str, Any] = {
            "title": local.title,
            "description": local.description,
            "priority": local.priority,
            "done": local.state == "done",
        }
        self.client.update_task(local.vikunja_task_id, payload)
        self.client.set_task_labels(local.vikunja_task_id, local.labels)
        if local.assignee:
            self.client.set_task_assignees(local.vikunja_task_id, [local.assignee])

    def _sync_meta_conflict(
        self,
        *,
        task_id: int,
        local_checksum: str,
        remote_updated: str | None,
    ) -> bool:
        meta = self.db.get_sync_meta(task_id)
        if not meta:
            return False
        local_changed = meta["local_checksum"] != local_checksum
        remote_changed = (meta["remote_updated"] or "") != (remote_updated or "")
        return local_changed and remote_changed

    def sync(
        self,
        *,
        direction: str,
        project_id: int,
        dry_run: bool = False,
        tasks_dir: Path | None = None,
        archive_dir: Path | None = None,
    ) -> SyncResult:
        if tasks_dir is not None:
            self.tasks_dir = tasks_dir
        if archive_dir is not None:
            self.tasks_done_dir = archive_dir

        result = SyncResult()
        self.tasks_dir.mkdir(parents=True, exist_ok=True)
        self.tasks_done_dir.mkdir(parents=True, exist_ok=True)

        local_files = sorted(self.tasks_dir.glob("TASK-*.yaml"))
        local_tasks: dict[int, tuple[TaskFile, Path, str]] = {}
        for file in local_files:
            task_file = TaskFile.from_path(file)
            local_tasks[task_file.vikunja_task_id] = (task_file, file, self._checksum(file))

        remote_tasks = self.client.list_tasks(project_id=project_id, limit=500)
        remote_by_id = {
            int(item["id"]): item
            for item in remote_tasks
            if item.get("id") is not None
        }

        for task_id, (local, path, checksum) in local_tasks.items():
            remote = remote_by_id.get(task_id)

            if remote is None:
                if direction in {"bidirectional", "local_to_remote"}:
                    if not dry_run:
                        created = self.client.create_task(
                            local.project_id,
                            {
                                "title": local.title,
                                "description": local.description,
                                "priority": local.priority,
                                "done": local.state == "done",
                            },
                        )
                        created_id = int(created["id"])
                        if created_id != local.vikunja_task_id:
                            local.vikunja_task_id = created_id
                            local.id = f"TASK-{created_id}"
                            local.write(path)
                        self.client.set_task_labels(created_id, local.labels)
                        if local.assignee:
                            self.client.set_task_assignees(created_id, [local.assignee])
                        self.db.upsert_mapping(local.id, created_id, local.source_ref)
                        self.db.upsert_sync_meta(
                            task_id=created_id,
                            local_file=str(path),
                            local_checksum=self._checksum(path),
                            remote_updated=self._remote_updated(created),
                        )
                    result.created_in_vikunja += 1
                continue

            remote_updated = self._remote_updated(remote)
            if self._sync_meta_conflict(
                task_id=task_id,
                local_checksum=checksum,
                remote_updated=remote_updated,
            ):
                result.conflicts.append(
                    SyncConflict(
                        local_file=str(path),
                        task_id=task_id,
                        reason="Both modified since last sync",
                    )
                )
                continue

            if direction in {"bidirectional", "local_to_remote"}:
                local_newer = (local.updated_at or "") > (remote_updated or "")
                if local_newer:
                    if not dry_run:
                        self._apply_local_to_remote(local, remote)
                    result.updated_in_vikunja += 1

            if direction in {"bidirectional", "remote_to_local"}:
                remote_newer = (remote_updated or "") > (local.updated_at or "")
                if remote_newer:
                    updated_local = self._task_from_remote(remote, project_id)
                    if not dry_run:
                        updated_local.write(path)
                    result.created_locally += 1

            if not dry_run:
                self.db.upsert_sync_meta(
                    task_id=task_id,
                    local_file=str(path),
                    local_checksum=self._checksum(path),
                    remote_updated=remote_updated,
                )

        if direction in {"bidirectional", "remote_to_local"}:
            for task_id, remote in remote_by_id.items():
                if task_id in local_tasks:
                    continue
                local = self._task_from_remote(remote, project_id)
                path = self._task_file_path(task_id)
                if not dry_run:
                    local.write(path)
                    self.db.upsert_sync_meta(
                        task_id=task_id,
                        local_file=str(path),
                        local_checksum=self._checksum(path),
                        remote_updated=self._remote_updated(remote),
                    )
                result.created_locally += 1

        return result
