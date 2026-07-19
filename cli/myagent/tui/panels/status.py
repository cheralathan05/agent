"""Bottom status bar for MyAgent TUI - single line, no borders."""

from rich.text import Text


class StatusBar:
    """Persistent bottom bar showing system state at a glance.
    
    Single line layout:
    BUILD │ main* │ +42 -12 │ Context 26% │ Ollama ● │ Working
    """

    def __init__(self):
        self.mode = "build"
        self.git_branch = "main"
        self.git_changes = 0
        self.git_additions = 0
        self.git_deletions = 0
        self.context_pct = 0
        self.model = "qwen3:8b"
        self.ollama_status = "checking"
        self.agent_state = "ready"
        self.has_repo = False

    def __rich__(self) -> Text:
        parts = []

        # Mode
        mode_color = {
            "plan": "blue", "build": "cyan", "debug": "magenta",
            "review": "yellow", "ask": "green",
        }.get(self.mode, "white")
        parts.append((f"  {self.mode.upper()} ", mode_color))

        parts.append((" │ ", "dim"))

        # Git
        if self.has_repo and self.git_branch:
            branch = self.git_branch
            if self.git_changes > 0:
                branch += "*"
            git_color = "yellow" if self.git_changes > 0 else "green"
            parts.append((branch, git_color))

            if self.git_additions > 0 or self.git_deletions > 0:
                diff_parts = []
                if self.git_additions > 0:
                    diff_parts.append(f"+{self.git_additions}")
                if self.git_deletions > 0:
                    diff_parts.append(f"-{self.git_deletions}")
                parts.append((" ", ""))
                parts.append((" ".join(diff_parts), "green" if self.git_additions > 0 else "red"))
            parts.append((" │ ", "dim"))

        # Context
        if self.context_pct > 0:
            pct_color = "green" if self.context_pct < 50 else "yellow" if self.context_pct < 80 else "red"
            parts.append((f"Context {self.context_pct:.0f}%", pct_color))
            parts.append((" │ ", "dim"))

        # Model
        parts.append((self.model, "bold yellow"))
        parts.append((" │ ", "dim"))

        # Ollama status
        status_icon, status_color = self._status_style()
        parts.append((f"{status_icon} Ollama", status_color))
        parts.append((" │ ", "dim"))

        # Agent state
        state_label = self._state_label()
        state_color = {
            "ready": "green", "thinking": "cyan", "planning": "blue",
            "reading": "cyan", "editing": "yellow", "running": "yellow",
            "testing": "magenta", "reviewing": "blue", "completed": "green",
            "error": "red",
        }.get(self.agent_state, "dim")
        parts.append((state_label, state_color))

        return Text.assemble(*parts)

    def _status_style(self) -> tuple[str, str]:
        mapping = {
            "connected": ("●", "green"),
            "ok": ("●", "green"),
            "processing": ("◐", "yellow"),
            "warning": ("⚠", "yellow"),
            "error": ("●", "red"),
            "unavailable": ("✗", "red"),
            "checking": ("◌", "dim"),
        }
        return mapping.get(self.ollama_status, ("◌", "dim"))

    def _state_label(self) -> str:
        labels = {
            "ready": "Ready", "thinking": "Thinking", "planning": "Planning",
            "reading": "Reading", "editing": "Editing", "running": "Working",
            "testing": "Testing", "reviewing": "Reviewing", "completed": "Completed",
            "error": "Error",
        }
        return labels.get(self.agent_state, "Idle")
