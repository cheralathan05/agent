"""Terminal command execution tools using the security sandbox."""

from __future__ import annotations

from typing import Any

from backend.app.security.sandbox import sandbox
from backend.app.tools.base import BaseTool


class RunCommandTool(BaseTool):
    name = "run_command"
    description = "Run a terminal command in the workspace"
    input_schema = {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "Command to execute"},
            "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 30},
        },
        "required": ["command"],
    }
    risk_level = "medium"
    permission_requirement = "confirmation"
    timeout = 120

    async def execute(self, command: str, timeout: int = 30, **kwargs) -> dict[str, Any]:
        """Execute a command using the sandbox."""
        # Execute through sandbox (sandbox handles command classification internally)
        result = await sandbox.execute(
            command=command,
            timeout=timeout or 30,
            cwd=kwargs.get("workspace"),
        )
        return result


class RunBackgroundCommandTool(BaseTool):
    name = "run_background_command"
    description = "Start a long-running command in the background"
    input_schema = {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "Command to start"},
        },
        "required": ["command"],
    }
    risk_level = "high"
    permission_requirement = "confirmation"
    timeout = 10

    _processes: dict[str, Any] = {}

    async def execute(self, command: str, **kwargs) -> dict[str, Any]:
        """Start a background process."""
        import asyncio
        from pathlib import Path

        from backend.app.config import settings
        from backend.app.tools.utils import _split_command

        ws = Path(kwargs.get("workspace") or settings.workspace_path).resolve()

        try:
            args = _split_command(command)
            if not args:
                return {"success": False, "output": "", "error": "Empty command"}

            proc = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(ws),
            )

            pid = str(id(proc))
            self._processes[pid] = proc
            return {
                "success": True,
                "output": f"Started background process (pid={pid})",
                "metadata": {"process_id": pid, "command": command},
            }
        except Exception as e:
            return {"success": False, "output": "", "error": str(e)}


class GetProcessOutputTool(BaseTool):
    name = "get_process_output"
    description = "Get output from a background process"
    input_schema = {
        "type": "object",
        "properties": {
            "process_id": {"type": "string", "description": "Process ID from run_background_command"},
        },
        "required": ["process_id"],
    }
    risk_level = "safe"
    timeout = 5

    async def execute(self, process_id: str, **kwargs) -> dict[str, Any]:
        """Check if a background process has output."""
        proc = RunBackgroundCommandTool._processes.get(process_id)
        if not proc:
            return {"success": False, "output": "", "error": "Process not found"}

        try:
            import asyncio
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=1
                )
                stdout_str = stdout.decode("utf-8", errors="replace") if stdout else ""
                stderr_str = stderr.decode("utf-8", errors="replace") if stderr else ""
                del RunBackgroundCommandTool._processes[process_id]
                return {
                    "success": proc.returncode == 0,
                    "output": stdout_str,
                    "error": stderr_str or None,
                    "metadata": {"completed": True, "exit_code": proc.returncode},
                }
            except asyncio.TimeoutError:
                return {
                    "success": True,
                    "output": "Process still running",
                    "metadata": {"completed": False},
                }
        except Exception as e:
            return {"success": False, "output": "", "error": str(e)}


class StopProcessTool(BaseTool):
    name = "stop_process"
    description = "Stop a running background process"
    input_schema = {
        "type": "object",
        "properties": {
            "process_id": {"type": "string", "description": "Process ID to stop"},
        },
        "required": ["process_id"],
    }
    risk_level = "medium"
    permission_requirement = "confirmation"
    timeout = 5

    async def execute(self, process_id: str, **kwargs) -> dict[str, Any]:
        """Stop a background process."""
        proc = RunBackgroundCommandTool._processes.get(process_id)
        if not proc:
            return {"success": False, "output": "", "error": "Process not found"}

        try:
            proc.kill()
            del RunBackgroundCommandTool._processes[process_id]
            return {"success": True, "output": f"Process {process_id} stopped"}
        except Exception as e:
            return {"success": False, "output": "", "error": str(e)}
