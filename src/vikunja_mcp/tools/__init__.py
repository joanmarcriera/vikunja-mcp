"""Vikunja MCP tool implementations."""

from vikunja_mcp.tools.add_execution_note import run as add_execution_note
from vikunja_mcp.tools.claim_next_task import run as claim_next_task
from vikunja_mcp.tools.create_task import run as create_task
from vikunja_mcp.tools.get_task import run as get_task
from vikunja_mcp.tools.list_tasks import run as list_tasks
from vikunja_mcp.tools.sync_fs_tasks import run as sync_fs_tasks
from vikunja_mcp.tools.transition_task import run as transition_task
from vikunja_mcp.tools.update_task import run as update_task

__all__ = [
    "list_tasks",
    "get_task",
    "create_task",
    "update_task",
    "transition_task",
    "claim_next_task",
    "add_execution_note",
    "sync_fs_tasks",
]
