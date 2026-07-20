"""Premium context sidebar with animated progress bars, live session timer, and enhanced git display."""

from pathlib import Path
from typing import Optional

from rich.console import Group, RenderableType
from rich.text import Text

from ..animation import AnimatedBar, _SUPPORTS_UNICODE


class ContextPanel:
    """Premium right sidebar with animated stats and live data."""

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
        self._frame = 0
        self._session_start = 0.0  # Set externally
        self._bar = AnimatedBar(12)

    def toggle_visibility(self):
        self.visible = not self.visible

    def tick(self):
        """Advance animation frames."""
        self._frame += 1
        self._bar.tick()

    def context_percent(self) -> float:
        if self.context_limit <= 0 or self.context_used <= 0:
            return 0.0
        return min(100.0, (self.context_used / self.context_limit) * 100.0)

    def __rich__(self) -> RenderableType:
        if not self.visible:
            return Text("")

        self.tick()
        elements = []

        # ── SECTION: MODEL ──
        elements.append(Text("  ── MODEL ──", "bold"))
        elements.append(Text(""))
        elements.append(Text(f"  {self.model}", "bold yellow"))
        elements.append(Text(f"  {self.provider}", "dim"))
        elements.append(Text(""))

        # Ollama status with pulsing dot
        status_icon, status_color = self._status_style()
        pulse_dot = "◉" if (self._frame // 4) % 2 == 0 else "●"
        if self.ollama_status in ("ok", "connected"):
            status_dot = pulse_dot
        else:
            status_dot = status_icon
        elements.append(Text.assemble(
            ("  ", ""),
            (f"{status_dot} ", status_color),
            (f"{self.ollama_status.capitalize()}", status_color),
        ))

        # ── SECTION: CONTEXT (always show) ──
        pct = self.context_percent()
        elements.append(Text(""))
        elements.append(Text("  ── CONTEXT ──", "bold"))
        elements.append(Text(""))
        elements.append(Text(f"  {self.context_used:,} / {self.context_limit:,}", "white"))

        # Animated progress bar
        bar = self._bar.render(pct, pulse=(pct > 0))
        bar_color = self._pct_color(pct)
        elements.append(Text.assemble(
            ("  ", ""),
            bar,
            (f"  {pct:.0f}%", bar_color),
        ))

        # ── SECTION: SESSION ──
        has_data = self.files_read > 0 or self.files_changed > 0 or self.commands_run > 0
        if has_data or True:  # Always show session now
            elements.append(Text(""))
            elements.append(Text("  ── SESSION ──", "bold"))
            elements.append(Text(""))
            
            # Session timer (if start set)
            if self._session_start > 0:
                import time
                elapsed = int(time.time() - self._session_start)
                m, s = divmod(elapsed, 60)
                time_str = f"{m:02d}:{s:02d}"
                # Pulsing clock icon
                clock_icon = "⏱" if (self._frame // 3) % 2 == 0 else "⏰"
                elements.append(Text(f"  {clock_icon} {time_str}", "bold white"))

            if self.files_read > 0:
                icon = "📄" if _SUPPORTS_UNICODE else "F"
                elements.append(Text(f"  {icon} {self.files_read} files read", "white"))
            if self.files_changed > 0:
                icon = "✏️" if _SUPPORTS_UNICODE else "C"
                elements.append(Text(f"  {icon} {self.files_changed} files changed", "yellow"))
            if self.commands_run > 0:
                icon = "⚡" if _SUPPORTS_UNICODE else ">"
                elements.append(Text(f"  {icon} {self.commands_run} commands", "white"))

        # ── SECTION: GIT ──
        if self._has_repo and self.git_branch:
            elements.append(Text(""))
            elements.append(Text("  ── GIT ──", "bold"))
            elements.append(Text(""))
            
            # Branch with animated icon
            branch_icon = "🌿" if _SUPPORTS_UNICODE else "B"
            branch_text = self.git_branch
            has_changes = self.git_changes > 0
            
            if has_changes:
                branch_text += " ●"
                elements.append(Text(f"  {branch_icon} {branch_text}", "yellow"))
            else:
                branch_text += " ✔"
                elements.append(Text(f"  {branch_icon} {branch_text}", "green"))
            
            if has_changes:
                diffs = []
                if self.git_additions > 0:
                    diffs.append(f"+{self.git_additions}")
                if self.git_deletions > 0:
                    diffs.append(f"-{self.git_deletions}")
                if diffs:
                    elements.append(Text(f"  {' '.join(diffs)}", "white"))
                
                # Show changed files count
                elements.append(Text(f"  {self.git_changes} file(s) changed", "dim"))

        # ── Decorative separator ──
        elements.append(Text(""))
        elements.append(Text(f"  {self._separator_line()}", "dim"))

        return Group(*elements) if elements else Text("")

    def _separator_line(self) -> str:
        """Animated decorative separator."""
        dots = ["·", "∙", "⋅", "∙"]
        idx = self._frame % len(dots)
        return dots[idx] * 8

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

    def _pct_color(self, pct: float) -> str:
        if pct < 50:
            return "green"
        elif pct < 80:
            return "yellow"
        return "red"
