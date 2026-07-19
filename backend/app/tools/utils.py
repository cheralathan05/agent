"""Shared utilities for tools."""

from pathlib import Path

from backend.app.config import settings


def resolve_path(path: str, workspace: str | None = None) -> Path:
    """Resolve a path relative to workspace, with path traversal protection."""
    base = Path(workspace or settings.workspace_path).resolve()
    target = (base / path).resolve()

    # Path traversal protection
    if not str(target).startswith(str(base)):
        raise ValueError(f"Path traversal detected: {path}")

    return target
