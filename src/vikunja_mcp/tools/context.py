"""Tool runtime context."""

from __future__ import annotations

from dataclasses import dataclass

from vikunja_mcp.config import Settings
from vikunja_mcp.db import LocalDB
from vikunja_mcp.sync_engine import SyncEngine
from vikunja_mcp.vikunja_client import VikunjaClient


@dataclass(slots=True)
class ToolContext:
    settings: Settings
    client: VikunjaClient
    db: LocalDB
    sync_engine: SyncEngine
