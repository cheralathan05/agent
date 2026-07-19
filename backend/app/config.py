"""Application configuration with layered priority: CLI > Environment > Config file > Defaults."""

import os
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5-coder"

    # Database
    database_url: str = "sqlite+aiosqlite:///./myagent.db"

    # Workspace
    workspace_root: str = "./workspace"

    # Agent Limits
    max_agent_steps: int = 30
    max_retries: int = 3
    max_tool_failures: int = 5
    command_timeout: int = 120
    model_timeout: int = 60
    context_limit: int = 8000
    max_file_size: int = 1048576  # 1MB
    max_output_size: int = 50000

    # Backend
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    # Logging
    log_level: str = "INFO"

    # Security
    allowed_paths: list[str] = []
    blocked_commands: list[str] = [
        "rm -rf /", "format", "mkfs", "dd if=",
        ":(){ :|:& };:", "wget", "curl -o",
    ]
    require_confirmation_commands: list[str] = [
        "npm install", "pip install", "git commit",
        "git push", "alembic upgrade", "drop table",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def workspace_path(self) -> Path:
        return Path(self.workspace_root).resolve()

    @property
    def database_sync_url(self) -> str:
        """Return sync database URL (strip aiosqlite prefix for sync usage)."""
        return self.database_url.replace("+aiosqlite", "")


settings = Settings()

# Override from environment variables explicitly
for field_name in Settings.model_fields:
    env_val = os.environ.get(field_name.upper())
    if env_val is not None:
        setattr(settings, field_name, env_val)
