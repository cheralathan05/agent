"""Tool registry for managing available tools."""

from __future__ import annotations

from typing import Any

from backend.app.tools.base import BaseTool


class ToolRegistry:
    """Registry of all available tools."""

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool):
        """Register a tool."""
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered")
        self._tools[tool.name] = tool

    def register_all(self, *tools: BaseTool):
        """Register multiple tools."""
        for tool in tools:
            self.register(tool)

    def get(self, name: str) -> BaseTool | None:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> list[dict[str, Any]]:
        """List all registered tools with metadata."""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema,
                "risk_level": tool.risk_level,
                "permission_requirement": tool.permission_requirement,
                "timeout": tool.timeout,
            }
            for tool in self._tools.values()
        ]

    async def execute(self, name: str, **kwargs) -> dict[str, Any]:
        """Execute a tool by name."""
        from backend.app.security.permissions import permission_engine
        from backend.app.security.secret_detector import secret_detector

        tool = self.get(name)
        if not tool:
            return {
                "success": False,
                "output": "",
                "error": f"Unknown tool: '{name}'",
            }

        # Check permission
        risk = tool.risk_level
        perm_check = await permission_engine.check_permission(
            tool_name=name,
            action=kwargs.get("action", str(kwargs.get("path", name))),
            reason=kwargs.get("reason", f"Execute {name}"),
            risk=risk,
            run_id=kwargs.get("run_id"),
        )
        if not perm_check.get("permitted"):
            return {
                "success": False,
                "output": "",
                "error": perm_check.get("message", "Permission denied"),
                "requires_approval": True,
                "approval_id": perm_check.get("approval_id"),
            }

        # Redact secrets from arguments before execution
        safe_kwargs = {}
        for key, val in kwargs.items():
            if isinstance(val, str) and secret_detector.contains_secrets(val):
                safe_kwargs[key] = secret_detector.redact(val)
            else:
                safe_kwargs[key] = val

        # Execute
        result = await tool.execute(**safe_kwargs)
        return result

    def __len__(self) -> int:
        return len(self._tools)


# Global registry
registry = ToolRegistry()


def init_tools():
    """Register all available tools."""
    from backend.app.tools.filesystem.read_write import (
        ReadFileTool,
        WriteFileTool,
        ListDirectoryTool,
        FileExistsTool,
    )
    from backend.app.tools.filesystem.edit import (
        EditFileTool,
        CreateFileTool,
        DeleteFileTool,
    )
    from backend.app.tools.search.code_search import (
        SearchFilesTool,
        SearchCodeTool,
        RegexSearchTool,
    )
    from backend.app.tools.terminal.run_command import (
        RunCommandTool,
        RunBackgroundCommandTool,
        GetProcessOutputTool,
        StopProcessTool,
    )
    from backend.app.tools.git.git_utils import (
        GitStatusTool,
        GitDiffTool,
        GitLogTool,
        GitBranchTool,
        GitCommitTool,
    )
    from backend.app.tools.testing.test_runner import (
        RunTestsTool,
        RunSpecificTestTool,
    )
    from backend.app.tools.project.detect import (
        DetectLanguageTool,
        DetectFrameworkTool,
        BuildProjectMapTool,
    )

    registry.register_all(
        # Filesystem tools
        ReadFileTool(),
        WriteFileTool(),
        ListDirectoryTool(),
        FileExistsTool(),
        EditFileTool(),
        CreateFileTool(),
        DeleteFileTool(),
        # Search tools
        SearchFilesTool(),
        SearchCodeTool(),
        RegexSearchTool(),
        # Terminal tools
        RunCommandTool(),
        RunBackgroundCommandTool(),
        GetProcessOutputTool(),
        StopProcessTool(),
        # Git tools
        GitStatusTool(),
        GitDiffTool(),
        GitLogTool(),
        GitBranchTool(),
        GitCommitTool(),
        # Testing tools
        RunTestsTool(),
        RunSpecificTestTool(),
        # Project tools
        DetectLanguageTool(),
        DetectFrameworkTool(),
        BuildProjectMapTool(),
    )
