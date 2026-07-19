"""Sandbox for safe command execution."""

from __future__ import annotations

import asyncio
import os
import shlex
from pathlib import Path
from typing import Any

from backend.app.config import settings
from backend.app.security.command_policy import command_policy as cp


class Sandbox:
    """Sandbox for executing terminal commands safely."""

    def __init__(self, workspace: str | Path | None = None):
        self.workspace = Path(workspace or settings.workspace_path).resolve()

    async def execute(
        self,
        command: str,
        timeout: int | None = None,
        cwd: str | Path | None = None,
        env: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Execute a command in the sandbox.
        
        Returns:
            Dict with 'success', 'output', 'error', 'exit_code', 'duration_ms'.
        """
        start_time = asyncio.get_event_loop().time()

        # Validate command
        classification = cp.classify(command)
        if classification.is_blocked:
            return {
                "success": False,
                "output": "",
                "error": f"Blocked command: {classification.reason}",
                "exit_code": -1,
                "duration_ms": 0,
            }

        # Determine working directory
        work_dir = Path(cwd or self.workspace).resolve()
        if not str(work_dir).startswith(str(self.workspace)):
            work_dir = self.workspace

        # Build safe environment
        safe_env = os.environ.copy()
        if env:
            safe_env.update(env)
        # Remove dangerous env vars
        safe_env.pop("AWS_SECRET_ACCESS_KEY", None)
        safe_env.pop("AWS_SESSION_TOKEN", None)
        safe_env.pop("GITHUB_TOKEN", None)

        timeout_seconds = timeout or settings.command_timeout

        try:
            # Use shell=False with shlex for safety
            if os.name == "nt":
                # Windows needs special handling
                proc = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=str(work_dir),
                    env=safe_env,
                )
            else:
                args = shlex.split(command)
                proc = await asyncio.create_subprocess_exec(
                    *args,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=str(work_dir),
                    env=safe_env,
                )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=timeout_seconds,
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                duration = int((asyncio.get_event_loop().time() - start_time) * 1000)
                return {
                    "success": False,
                    "output": "",
                    "error": f"Command timed out after {timeout_seconds}s",
                    "exit_code": -1,
                    "duration_ms": duration,
                }

            duration = int((asyncio.get_event_loop().time() - start_time) * 1000)
            stdout_str = stdout.decode("utf-8", errors="replace") if stdout else ""
            stderr_str = stderr.decode("utf-8", errors="replace") if stderr else ""

            # Truncate output if too large
            max_output = settings.max_output_size
            if len(stdout_str) > max_output:
                stdout_str = stdout_str[:max_output] + f"\n... [truncated {len(stdout_str) - max_output} more chars]"

            return {
                "success": proc.returncode == 0,
                "output": stdout_str,
                "error": stderr_str if stderr_str else None,
                "exit_code": proc.returncode or 0,
                "duration_ms": duration,
            }

        except FileNotFoundError as e:
            return {
                "success": False,
                "output": "",
                "error": f"Command not found: {e}",
                "exit_code": -1,
                "duration_ms": 0,
            }
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": f"Execution error: {str(e)}",
                "exit_code": -1,
                "duration_ms": 0,
            }

    async def check_command(self, command: str) -> dict[str, Any]:
        """Check if a command is allowed without executing it."""
        classification = cp.classify(command)
        return {
            "allowed": not classification.is_blocked,
            "requires_confirmation": classification.requires_confirmation,
            "classification": classification.classification,
            "reason": classification.reason,
        }


# Global sandbox instance
sandbox = Sandbox()
