"""SQLite persistence for idempotency, mappings, locks, and sync metadata."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path


class LocalDB:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _initialize(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS idempotency_keys (
                    key TEXT PRIMARY KEY,
                    task_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS claim_locks (
                    lock_key TEXT PRIMARY KEY,
                    holder TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS task_mappings (
                    local_id TEXT PRIMARY KEY,
                    task_id INTEGER NOT NULL,
                    source_ref TEXT UNIQUE,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS sync_metadata (
                    task_id INTEGER PRIMARY KEY,
                    local_file TEXT NOT NULL,
                    local_checksum TEXT NOT NULL,
                    remote_updated TEXT,
                    last_sync TEXT NOT NULL
                );
                """
            )

    def get_idempotency_task_id(self, key: str) -> int | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT task_id FROM idempotency_keys WHERE key = ?",
                (key,),
            ).fetchone()
            return int(row["task_id"]) if row else None

    def set_idempotency_task_id(self, key: str, task_id: int) -> None:
        now = datetime.now(UTC).isoformat()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO idempotency_keys(key, task_id, created_at)
                VALUES(?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET task_id = excluded.task_id
                """,
                (key, task_id, now),
            )

    def acquire_lock(self, lock_key: str, holder: str, ttl_seconds: int = 30) -> bool:
        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=ttl_seconds)
        with self.connect() as conn:
            row = conn.execute(
                "SELECT expires_at FROM claim_locks WHERE lock_key = ?", (lock_key,)
            ).fetchone()
            if row:
                existing_expiry = datetime.fromisoformat(row["expires_at"])
                if existing_expiry > now:
                    return False
            conn.execute(
                """
                INSERT INTO claim_locks(lock_key, holder, expires_at)
                VALUES(?, ?, ?)
                ON CONFLICT(lock_key)
                DO UPDATE SET holder = excluded.holder, expires_at = excluded.expires_at
                """,
                (lock_key, holder, expires_at.isoformat()),
            )
            return True

    def release_lock(self, lock_key: str) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM claim_locks WHERE lock_key = ?", (lock_key,))

    def upsert_mapping(self, local_id: str, task_id: int, source_ref: str | None = None) -> None:
        now = datetime.now(UTC).isoformat()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO task_mappings(local_id, task_id, source_ref, updated_at)
                VALUES(?, ?, ?, ?)
                ON CONFLICT(local_id)
                DO UPDATE SET task_id = excluded.task_id,
                              source_ref = excluded.source_ref,
                              updated_at = excluded.updated_at
                """,
                (local_id, task_id, source_ref, now),
            )

    def find_task_by_source_ref(self, source_ref: str) -> int | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT task_id FROM task_mappings WHERE source_ref = ?", (source_ref,)
            ).fetchone()
            return int(row["task_id"]) if row else None

    def get_sync_meta(self, task_id: int) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute(
                "SELECT * FROM sync_metadata WHERE task_id = ?", (task_id,)
            ).fetchone()

    def upsert_sync_meta(
        self,
        *,
        task_id: int,
        local_file: str,
        local_checksum: str,
        remote_updated: str | None,
    ) -> None:
        now = datetime.now(UTC).isoformat()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO sync_metadata(
                    task_id, local_file, local_checksum, remote_updated, last_sync
                )
                VALUES(?, ?, ?, ?, ?)
                ON CONFLICT(task_id)
                DO UPDATE SET local_file = excluded.local_file,
                              local_checksum = excluded.local_checksum,
                              remote_updated = excluded.remote_updated,
                              last_sync = excluded.last_sync
                """,
                (task_id, local_file, local_checksum, remote_updated, now),
            )
