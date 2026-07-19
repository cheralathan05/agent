"""Git integration tools with async subprocess."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from backend.app.config import settings
from backend.app.tools.base import BaseTool


async def _run_git_async(args: list[str], cwd: str | Path, timeout: int = 30) -> dict[str, Any]:
    """Run a git command asynchronously."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "git", *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(cwd),
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
            return {
                "success": proc.returncode == 0,
                "output": stdout.decode("utf-8", errors="replace").strip(),
                "error": stderr.decode("utf-8", errors="replace").strip(),
                "exit_code": proc.returncode or 0,
            }
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return {
                "success": False, "output": "", "error": "Git command timed out",
                "exit_code": -1,
            }
    except FileNotFoundError:
        return {"success": False, "output": "", "error": "Git not found", "exit_code": -1}
    except Exception as e:
        return {"success": False, "output": "", "error": str(e), "exit_code": -1}


class GitStatusTool(BaseTool):
    name = "git_status"
    description = "Show the working tree status"
    input_schema = {"type": "object", "properties": {}, "required": []}
    risk_level = "safe"
    timeout = 15

    async def execute(self, **kwargs) -> dict[str, Any]:
        ws = Path(kwargs.get("workspace") or settings.workspace_path)
        return await _run_git_async(["status"], cwd=ws)


class GitDiffTool(BaseTool):
    name = "git_diff"
    description = "Show changes in the working tree"
    input_schema = {"type": "object", "properties": {}, "required": []}
    risk_level = "safe"
    timeout = 15

    async def execute(self, **kwargs) -> dict[str, Any]:
        ws = Path(kwargs.get("workspace") or settings.workspace_path)
        return await _run_git_async(["diff"], cwd=ws)


class GitLogTool(BaseTool):
    name = "git_log"
    description = "Show commit logs"
    input_schema = {"type": "object", "properties": {"count": {"type": "integer", "default": 10}}, "required": []}
    risk_level = "safe"
    timeout = 15

    async def execute(self, count: int = 10, **kwargs) -> dict[str, Any]:
        ws = Path(kwargs.get("workspace") or settings.workspace_path)
        return await _run_git_async(
            ["log", f"--max-count={count}", "--oneline", "--decorate"], cwd=ws
        )


class GitBranchTool(BaseTool):
    name = "git_branch"
    description = "List or detect current branch"
    input_schema = {"type": "object", "properties": {}, "required": []}
    risk_level = "safe"
    timeout = 15

    async def execute(self, **kwargs) -> dict[str, Any]:
        ws = Path(kwargs.get("workspace") or settings.workspace_path)
        return await _run_git_async(["rev-parse", "--abbrev-ref", "HEAD"], cwd=ws)


class GitCommitTool(BaseTool):
    name = "git_commit"
    description = "Create a commit with staged changes"
    input_schema = {"type": "object", "properties": {"message": {"type": "string"}}, "required": ["message"]}
    risk_level = "medium"
    permission_requirement = "confirmation"
    timeout = 15

    async def execute(self, message: str, **kwargs) -> dict[str, Any]:
        ws = Path(kwargs.get("workspace") or settings.workspace_path)
        return await _run_git_async(["commit", "-m", message], cwd=ws)
