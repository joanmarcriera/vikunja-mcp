"""Configuration loading for vikunja-mcp-server."""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    vikunja_base_url: str = Field(alias="VIKUNJA_BASE_URL")
    vikunja_token: str = Field(alias="VIKUNJA_TOKEN")
    vikunja_default_project_id: int = Field(alias="VIKUNJA_DEFAULT_PROJECT_ID")
    vikunja_verify_ssl: bool = Field(default=True, alias="VIKUNJA_VERIFY_SSL")
    vikunja_max_page_size: int = Field(default=100, alias="VIKUNJA_MAX_PAGE_SIZE")
    vikunja_max_fetch_tasks: int = Field(default=500, alias="VIKUNJA_MAX_FETCH_TASKS")

    mcp_log_level: str = Field(default="INFO", alias="MCP_LOG_LEVEL")
    mcp_sqlite_path: Path = Field(
        default=Path(".orchestrator/vikunja_mcp.db"), alias="MCP_SQLITE_PATH"
    )

    tasks_dir: Path = Field(default=Path("tasks"), alias="TASKS_DIR")
    tasks_done_dir: Path = Field(default=Path("tasks_done"), alias="TASKS_DONE_DIR")
    outputs_dir: Path = Field(default=Path("outputs"), alias="OUTPUTS_DIR")
    agent_name: str = Field(default="pm.agent", alias="AGENT_NAME")

    @field_validator("vikunja_base_url")
    @classmethod
    def normalize_base_url(cls, value: str) -> str:
        trimmed = value.strip().rstrip("/")
        if not trimmed.endswith("/api/v1"):
            trimmed = f"{trimmed}/api/v1"
        return trimmed

    @classmethod
    def load(cls) -> Settings:
        load_dotenv()
        settings = cls()
        settings.ensure_dirs()
        return settings

    def ensure_dirs(self) -> None:
        self.tasks_dir.mkdir(parents=True, exist_ok=True)
        self.tasks_done_dir.mkdir(parents=True, exist_ok=True)
        self.outputs_dir.mkdir(parents=True, exist_ok=True)
        self.mcp_sqlite_path.parent.mkdir(parents=True, exist_ok=True)
