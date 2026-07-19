"""Shared utilities for tools."""

from __future__ import annotations

import asyncio
import os
import shlex
from pathlib import Path
from typing import Any

from backend.app.config import settings


def resolve_path(path: str, workspace: str | None = None) -> Path:
    """Resolve a path relative to workspace, with path traversal protection."""
    base = Path(workspace or settings.workspace_path).resolve()
    target = (base / path).resolve()

    # Path traversal protection
    if not str(target).startswith(str(base)):
        raise ValueError(f"Path traversal detected: {path}")

    return target


def _split_command(command: str) -> list[str]:
    """Split a command string into args, cross-platform safe.
    
    Uses shlex.split with posix=False on Windows for better compatibility.
    Falls back to simple whitespace split if shlex fails.
    """
    try:
        return shlex.split(command, posix=os.name != "nt")
    except ValueError:
        # If shlex fails, fall back to simple split
        return command.split()


async def run_cmd_async(
    args: list[str],
    cwd: str | Path | None = None,
    timeout: int = 30,
) -> dict[str, Any]:
    """Run a command asynchronously and return the result.
    
    Uses create_subprocess_exec (shell=False) to prevent shell injection.
    
    Returns:
        Dict with keys: success, stdout, stderr, exit_code
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(cwd) if cwd else None,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            return {
                "success": proc.returncode == 0,
                "stdout": stdout.decode("utf-8", errors="replace") if stdout else "",
                "stderr": stderr.decode("utf-8", errors="replace") if stderr else "",
                "exit_code": proc.returncode or 0,
            }
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return {"success": False, "stdout": "", "stderr": "Command timed out", "exit_code": -1}
    except FileNotFoundError:
        return {"success": False, "stdout": "", "stderr": "Command not found", "exit_code": -1}
    except Exception as e:
        return {"success": False, "stdout": "", "stderr": str(e), "exit_code": -1}
