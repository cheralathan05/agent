"""Context sidebar panel - compact, shows only real information."""

from pathlib import Path
from typing import Optional

from rich.console import Group, RenderableType
from rich.text import Text


class ContextPanel:
    """Compact right sidebar showing model info, session stats, and git status.
    
    Only shows data that has actual values - no fake zeros or empty stats.
    """

    def __init__(self):
        self.model = "qwen3:8b"
        self.provider = "Ollama · Local"
        self.ollama_status = "checking"
        self.context_used = 0
        self.context_limit = 32000
        self.workspace = Path(".").resolve()
        self.files_read = 0
        self.files_changed = 0
        self.commands_run = 0
        self.git_branch: Optional[str] = None
        self.git_changes = 0
        self.git_additions = 0
        self.git_deletions = 0
        self.mode = "build"
        self.visible = True
        self._has_repo = False

    def toggle_visibility(self):
        self.visible = not self.visible

    def context_percent(self) -> float:
        if self.context_limit <= 0 or self.context_used <= 0:
            return 0.0
        return min(100.0, (self.context_used / self.context_limit) * 100.0)

    def __rich__(self) -> RenderableType:
        if not self.visible:
            return Text("")

        elements = []

        # ── MODEL section ──
        elements.append(Text("  MODEL", "bold"))
        elements.append(Text(""))
        elements.append(Text(f"  {self.model}", "bold yellow"))
        elements.append(Text(f"  {self.provider}", "dim"))
        elements.append(Text(""))

        # Ollama status
        status_icon, status_color = self._status_style()
        elements.append(Text.assemble(
            ("  ", ""),
            (f"{status_icon} ", status_color),
            (f"{self.ollama_status.capitalize()}", status_color),
        ))

        # ── CONTEXT section ──
        pct = self.context_percent()
        if pct > 0:
            elements.append(Text(""))
            elements.append(Text("  CONTEXT", "bold"))
            elements.append(Text(""))
            elements.append(Text(f"  {self.context_used:,} / {self.context_limit:,}", "white"))
            bar = self._render_bar(pct)
            elements.append(Text.assemble(
                ("  ", ""),
                bar,
                (f"  {pct:.0f}%", self._pct_color(pct)),
            ))

        # ── SESSION section (only if there's data) ──
        has_session_data = self.files_read > 0 or self.files_changed > 0 or self.commands_run > 0
        if has_session_data:
            elements.append(Text(""))
            elements.append(Text("  SESSION", "bold"))
            elements.append(Text(""))
            if self.files_read > 0:
                elements.append(Text(f"  {self.files_read} files read", "white"))
            if self.files_changed > 0:
                elements.append(Text(f"  {self.files_changed} files changed", "yellow"))
            if self.commands_run > 0:
                elements.append(Text(f"  {self.commands_run} commands", "white"))

        # ── GIT section (only if repository detected) ──
        if self._has_repo and self.git_branch:
            elements.append(Text(""))
            elements.append(Text("  GIT", "bold"))
            elements.append(Text(""))
            branch_text = self.git_branch
            if self.git_changes > 0:
                branch_text += "*"
            elements.append(Text(f"  {branch_text}", "yellow" if self.git_changes > 0 else "green"))
            if self.git_changes > 0:
                diffs = []
                if self.git_additions > 0:
                    diffs.append(f"+{self.git_additions}")
                if self.git_deletions > 0:
                    diffs.append(f"-{self.git_deletions}")
                if diffs:
                    elements.append(Text(f"  {' '.join(diffs)}", "white"))

        return Group(*elements) if elements else Text("")

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

    def _render_bar(self, pct: float) -> Text:
        bar_len = 10
        filled = int(bar_len * pct / 100)
        bar = "█" * filled + "░" * (bar_len - filled)
        return Text(bar, style=self._pct_color(pct))

    def _pct_color(self, pct: float) -> str:
        if pct < 50:
            return "green"
        elif pct < 80:
            return "yellow"
        return "red"
