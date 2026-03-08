"""CLI entrypoint for vikunja-mcp-server."""

from __future__ import annotations

from pathlib import Path

import typer

from vikunja_mcp.config import Settings
from vikunja_mcp.db import LocalDB
from vikunja_mcp.logging_utils import configure_logging
from vikunja_mcp.mcp_server import create_mcp_server
from vikunja_mcp.schemas.tool_io import ClaimNextTaskInput, SyncFsTasksInput
from vikunja_mcp.sync_engine import SyncEngine
from vikunja_mcp.tools.claim_next_task import run as claim_next_task
from vikunja_mcp.tools.context import ToolContext
from vikunja_mcp.tools.sync_fs_tasks import run as sync_fs_tasks
from vikunja_mcp.vikunja_client import VikunjaClient

app = typer.Typer(add_completion=False, no_args_is_help=True)


def build_context(settings: Settings) -> tuple[ToolContext, VikunjaClient]:
    client = VikunjaClient(
        settings.vikunja_base_url,
        settings.vikunja_token,
        verify_ssl=settings.vikunja_verify_ssl,
    )
    db = LocalDB(settings.mcp_sqlite_path)
    sync_engine = SyncEngine(
        client=client,
        db=db,
        tasks_dir=settings.tasks_dir,
        tasks_done_dir=settings.tasks_done_dir,
    )
    return ToolContext(settings=settings, client=client, db=db, sync_engine=sync_engine), client


@app.command()
def serve(transport: str = typer.Option("stdio", help="MCP transport, usually stdio.")) -> None:
    """Run the MCP server."""
    settings = Settings.load()
    configure_logging(settings.mcp_log_level)
    ctx, client = build_context(settings)
    try:
        mcp = create_mcp_server(ctx)
        try:
            mcp.run(transport=transport)
        except TypeError:
            mcp.run()
    finally:
        client.close()


@app.command()
def doctor() -> None:
    """Validate environment and upstream connectivity."""
    settings = Settings.load()
    configure_logging(settings.mcp_log_level)
    issues: list[str] = []

    for env_name in (
        "VIKUNJA_BASE_URL",
        "VIKUNJA_TOKEN",
        "VIKUNJA_DEFAULT_PROJECT_ID",
    ):
        if not getattr(settings, env_name.lower()):
            issues.append(f"missing env var: {env_name}")

    settings.ensure_dirs()
    if not settings.mcp_sqlite_path.parent.exists():
        issues.append(f"sqlite directory not writable: {settings.mcp_sqlite_path.parent}")

    try:
        ctx, client = build_context(settings)
        try:
            client.check_auth()
            client.get_project(settings.vikunja_default_project_id)
        finally:
            client.close()
    except Exception as exc:  # pragma: no cover - network dependent
        issues.append(f"vikunja check failed: {exc}")

    if issues:
        for issue in issues:
            typer.echo(f"[FAIL] {issue}")
        raise typer.Exit(code=1)

    typer.echo("[OK] environment")
    typer.echo("[OK] vikunja reachable")
    typer.echo("[OK] sqlite writable")
    typer.echo("[OK] task directories available")


@app.command("sync")
def sync_command(
    project_id: int = typer.Option(..., "--project-id", help="Vikunja project id"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview changes without writing"),
    direction: str = typer.Option(
        "bidirectional",
        help="bidirectional/local_to_remote/remote_to_local",
    ),
    tasks_dir: Path | None = typer.Option(None, help="Override tasks directory"),
    archive_dir: Path | None = typer.Option(None, help="Override archive directory"),
) -> None:
    """Synchronize local task manifests with Vikunja."""
    settings = Settings.load()
    configure_logging(settings.mcp_log_level)
    ctx, client = build_context(settings)
    try:
        payload = SyncFsTasksInput(
            direction=direction,
            tasks_dir=str(tasks_dir) if tasks_dir else None,
            archive_dir=str(archive_dir) if archive_dir else None,
            project_id=project_id,
            dry_run=dry_run,
        )
        result = sync_fs_tasks(ctx, payload)
    finally:
        client.close()

    typer.echo(result)


@app.command("claim-next")
def claim_next(
    project_id: int = typer.Option(..., "--project-id", help="Vikunja project id"),
    agent: str = typer.Option(..., "--agent", help="Agent name"),
    accepted_label: list[str] = typer.Option(
        [],
        "--accepted-label",
        help="Label that must exist",
    ),
    exclude_label: list[str] = typer.Option([], "--exclude-label", help="Label to exclude"),
    limit_search: int = typer.Option(20, "--limit-search", help="Search window"),
) -> None:
    """Claim next deterministic eligible task for an agent."""
    settings = Settings.load()
    configure_logging(settings.mcp_log_level)
    ctx, client = build_context(settings)
    try:
        payload = ClaimNextTaskInput(
            project_id=project_id,
            agent_name=agent,
            accepted_labels=accepted_label,
            exclude_labels=exclude_label,
            limit_search=limit_search,
        )
        result = claim_next_task(ctx, payload)
    finally:
        client.close()

    typer.echo(result)


if __name__ == "__main__":
    app()
