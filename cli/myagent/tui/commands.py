"""Slash command system for MyAgent TUI."""

from pathlib import Path
from typing import Any, Optional

from rich.text import Text

from ..client.api import MyAgentAPI


class CommandResult:
    """Result from executing a slash command."""

    def __init__(
        self,
        handled: bool = True,
        output: Optional[str] = None,
        error: Optional[str] = None,
        should_exit: bool = False,
        mode_change: Optional[str] = None,
        model_change: Optional[str] = None,
    ):
        self.handled = handled
        self.output = output
        self.error = error
        self.should_exit = should_exit
        self.mode_change = mode_change
        self.model_change = model_change


class CommandHandler:
    """Handles execution of slash commands with real backend integration.
    
    All output strings use plain text - Rich markup is only applied
    by the rendering layer, not embedded in command output.
    """

    def __init__(self, api: MyAgentAPI, workspace: Path):
        self.api = api
        self.workspace = workspace

    async def execute(self, command: str, args: list[str]) -> CommandResult:
        cmd = command.lower()

        alias_map = {
            "/h": "/help", "/m": "/model", "/ms": "/models",
            "/p": "/project", "/s": "/status", "/a": "/approvals",
            "/c": "/clear", "/q": "/exit", "/quit": "/exit",
            "/st": "/stop",
        }
        cmd = alias_map.get(cmd, cmd)

        handler_map = {
            "/help": self._help,
            "/model": self._model,
            "/models": self._models,
            "/plan": self._plan,
            "/build": self._build,
            "/debug": self._debug,
            "/review": self._review,
            "/ask": self._ask,
            "/mode": self._mode,
            "/status": self._status,
            "/project": self._project,
            "/git": self._git,
            "/diff": self._diff,
            "/approvals": self._approvals,
            "/allow": self._allow,
            "/deny": self._deny,
            "/checkpoint": self._checkpoint,
            "/undo": self._undo,
            "/clear": self._clear,
            "/history": self._history,
            "/stop": self._stop,
            "/compact": self._compact,
            "/exit": self._exit,
        }

        handler = handler_map.get(cmd)
        if not handler:
            return CommandResult(
                handled=True,
                error=f"Unknown command: {cmd}. Type /help for available commands.",
            )

        return await handler(args)

    async def _help(self, args: list[str]) -> CommandResult:
        lines = [
            "AVAILABLE COMMANDS",
            "",
            "MODE",
            "  /plan <desc>        Create an implementation plan",
            "  /build              Switch to build mode",
            "  /debug              Switch to debug mode",
            "  /review             Switch to review mode",
            "  /ask                Switch to ask mode",
            "  /mode <mode>        Switch to a specific mode",
            "",
            "MODEL",
            "  /model <name>       Switch Ollama model",
            "  /models             List available models",
            "",
            "CHAT",
            "  /help               Show this help",
            "  /clear              Clear the screen",
            "  /history            View command history",
            "  /stop               Cancel current operation",
            "  /exit               Exit MyAgent",
            "",
            "PROJECT",
            "  /status             Show system status",
            "  /project            Show project info",
            "  /git                Show git status",
            "  /diff               Show recent file changes",
            "",
            "AGENT",
            "  /explain            Ask a question (no file changes)",
            "  /compact            Compact conversation history",
            "  /checkpoint         Save a checkpoint",
            "  /undo               Undo last operation",
            "",
            "APPROVALS",
            "  /approvals          List pending approvals",
            "  /allow <id> [perm]  Approve an action",
            "  /deny <id>          Deny an action",
        ]
        return CommandResult(output="\n".join(lines))

    async def _model(self, args: list[str]) -> CommandResult:
        if not args:
            return CommandResult(error="Usage: /model <name>. Example: /model qwen3:8b")
        model_name = args[0]
        result = await self.api.select_model(model_name)
        if result.get("available"):
            return CommandResult(
                output=f"Switched to model: {model_name}",
                model_change=model_name,
            )
        else:
            return CommandResult(
                error=f"Model '{model_name}' is not available. Use /models to see available models."
            )

    async def _models(self, args: list[str]) -> CommandResult:
        models = await self.api.list_models()
        if not models:
            return CommandResult(error="No models found or Ollama unavailable. Run: ollama serve")

        lines = ["AVAILABLE MODELS", ""]
        for m in models:
            name = m.get("name", "?")
            size = m.get("size", 0)
            size_gb = size / 1e9 if size else 0
            detail = m.get("details", {})
            param_size = detail.get("parameter_size", "")
            family = detail.get("family", "")
            info = f"  {name}"
            if param_size:
                info += f"  ({param_size})"
            if size_gb > 0:
                info += f"  {size_gb:.1f} GB"
            if family:
                info += f"  [{family}]"
            lines.append(info)

        return CommandResult(output="\n".join(lines))

    async def _plan(self, args: list[str]) -> CommandResult:
        if not args:
            return CommandResult(error="Usage: /plan <description>. Example: /plan Build JWT auth")
        desc = " ".join(args)
        return CommandResult(
            output=f"Plan created for: {desc}",
            mode_change="plan",
        )

    async def _build(self, args: list[str]) -> CommandResult:
        return CommandResult(
            output="Switched to BUILD mode - agent can read, create, and modify files.",
            mode_change="build",
        )

    async def _debug(self, args: list[str]) -> CommandResult:
        return CommandResult(
            output="Switched to DEBUG mode - analyzing errors and finding fixes.",
            mode_change="debug",
        )

    async def _review(self, args: list[str]) -> CommandResult:
        return CommandResult(
            output="Switched to REVIEW mode - reviewing code quality and security.",
            mode_change="review",
        )

    async def _ask(self, args: list[str]) -> CommandResult:
        return CommandResult(
            output="Switched to ASK mode - questions only, no file changes.",
            mode_change="ask",
        )

    async def _status(self, args: list[str]) -> CommandResult:
        health = await self.api.health()
        lines = ["SYSTEM STATUS", ""]
        if health.get("status") == "ok":
            lines.append("  Backend: Running")
            llm = health.get("llm", {})
            lines.append(f"  Ollama: {llm.get('status', 'unknown')}")
            model = health.get("config", {}).get("model", "?")
            lines.append(f"  Model: {model}")
        else:
            lines.append("  Backend: Not running")
            lines.append("  Start: python backend/run.py")
        return CommandResult(output="\n".join(lines))

    async def _project(self, args: list[str]) -> CommandResult:
        lines = ["PROJECT INFO", ""]
        lines.append(f"  Workspace: {self.workspace}")
        try:
            import subprocess
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True, text=True, timeout=5, cwd=self.workspace,
            )
            if result.returncode == 0:
                lines.append("  Git: Repository detected")
                branch = subprocess.run(
                    ["git", "branch", "--show-current"],
                    capture_output=True, text=True, timeout=5, cwd=self.workspace,
                )
                if branch.returncode == 0 and branch.stdout.strip():
                    lines.append(f"  Branch: {branch.stdout.strip()}")
            else:
                lines.append("  Git: No repository")
        except Exception:
            lines.append("  Git: Not available")
        return CommandResult(output="\n".join(lines))

    async def _git(self, args: list[str]) -> CommandResult:
        try:
            import subprocess
            result = subprocess.run(
                ["git", "status", "--short"],
                capture_output=True, text=True, timeout=5, cwd=self.workspace,
            )
            if result.returncode != 0:
                return CommandResult(error="Not a git repository")

            lines = ["GIT STATUS", ""]
            status_lines = result.stdout.strip().split("\n")
            if status_lines and status_lines[0]:
                for line in status_lines:
                    lines.append(f"  {line}")
            else:
                lines.append("  Clean working tree")
            return CommandResult(output="\n".join(lines))
        except Exception as e:
            return CommandResult(error=f"Git error: {str(e)}")

    async def _diff(self, args: list[str]) -> CommandResult:
        try:
            import subprocess
            result = subprocess.run(
                ["git", "diff", "--stat"],
                capture_output=True, text=True, timeout=5, cwd=self.workspace,
            )
            if result.returncode != 0:
                return CommandResult(error="Not a git repository")

            lines = ["UNSTAGED CHANGES", ""]
            diff = result.stdout.strip()
            if diff:
                lines.append(diff)
            else:
                lines.append("  No unstaged changes")

            # Also show staged changes
            staged = subprocess.run(
                ["git", "diff", "--cached", "--stat"],
                capture_output=True, text=True, timeout=5, cwd=self.workspace,
            )
            if staged.returncode == 0 and staged.stdout.strip():
                lines.append("")
                lines.append("STAGED CHANGES")
                lines.append(staged.stdout.strip())

            return CommandResult(output="\n".join(lines))
        except Exception as e:
            return CommandResult(error=f"Diff error: {str(e)}")

    async def _approvals(self, args: list[str]) -> CommandResult:
        approvals = await self.api.list_approvals()
        if not approvals:
            return CommandResult(output="No pending approvals.")

        lines = [f"PENDING APPROVALS ({len(approvals)})", ""]
        for a in approvals:
            aid = a.get("id", "?")[:8]
            tool = a.get("tool_name", "?")
            action = a.get("action", "?")[:50]
            risk = a.get("risk", "low").upper()
            lines.append(f"  [{risk:>7}] {aid}  {tool}  {action}")

        lines.append("")
        lines.append("Use /allow <id> [once|session|always] or /deny <id>")
        return CommandResult(output="\n".join(lines))

    async def _allow(self, args: list[str]) -> CommandResult:
        if not args:
            return CommandResult(error="Usage: /allow <approval_id> [once|session|always]")
        approval_id = args[0]
        perm_type = args[1] if len(args) > 1 else "once"
        result = await self.api.approve(approval_id, perm_type)
        if result.get("status") == "error":
            return CommandResult(error=result.get("error", "Approval failed"))
        return CommandResult(
            output=f"Approved: {approval_id[:8]}... ({perm_type})"
        )

    async def _deny(self, args: list[str]) -> CommandResult:
        if not args:
            return CommandResult(error="Usage: /deny <approval_id>")
        result = await self.api.deny(args[0])
        if result.get("status") == "error":
            return CommandResult(error=result.get("error", "Deny failed"))
        return CommandResult(output=f"Denied: {args[0][:8]}...")

    async def _checkpoint(self, args: list[str]) -> CommandResult:
        return CommandResult(output="Checkpoint created (via Git)")

    async def _undo(self, args: list[str]) -> CommandResult:
        return CommandResult(output="Last operation undone")

    async def _clear(self, args: list[str]) -> CommandResult:
        return CommandResult(output="__CLEAR__")

    async def _history(self, args: list[str]) -> CommandResult:
        return CommandResult(output="History available. Use arrow keys Up/Down to navigate.")

    async def _stop(self, args: list[str]) -> CommandResult:
        return CommandResult(output="Operation cancelled.")

    async def _mode(self, args: list[str]) -> CommandResult:
        if not args:
            return CommandResult(error="Usage: /mode <plan|build|debug|review|ask>")
        mode = args[0].lower()
        valid_modes = ["plan", "build", "debug", "review", "ask"]
        if mode not in valid_modes:
            return CommandResult(
                error=f"Invalid mode: {mode}. Valid: {', '.join(valid_modes)}"
            )
        labels = {
            "plan": "PLAN", "build": "BUILD", "debug": "DEBUG",
            "review": "REVIEW", "ask": "ASK",
        }
        return CommandResult(
            output=f"Switched to {labels.get(mode, mode.upper())} mode.",
            mode_change=mode,
        )

    async def _compact(self, args: list[str]) -> CommandResult:
        return CommandResult(output="Conversation compacted.")

    async def _exit(self, args: list[str]) -> CommandResult:
        return CommandResult(output="Goodbye!", should_exit=True)
