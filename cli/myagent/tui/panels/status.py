"""Premium bottom status bar with live data, animations, and session stats.

Single line layout:
  BUILD │ main* │ +42 -12 │ Context 26% │ 05:23 │ qwen3:8b │ ◉ Ollama │ Thinking
"""

import time

from rich.text import Text


class StatusBar:
    """Animated bottom bar with live session timer, git changes, and agent state."""

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
        self.session_start = 0.0
        self.message_count = 0
        self.response_time = 0.0
        self._frame = 0

    def tick(self):
        """Advance animation frame."""
        self._frame += 1

    def __rich__(self) -> Text:
        self.tick()
        parts = []

        # ── Mode with gradient-like effect ──
        mode_color = {
            "plan": "blue", "build": "cyan", "debug": "magenta",
            "review": "yellow", "ask": "green",
        }.get(self.mode, "white")
        
        # Animated mode indicator - pulse on certain states
        if self.agent_state in ("thinking", "running", "editing"):
            # Breathing effect
            if (self._frame // 6) % 2 == 0:
                parts.append((f"  {self.mode.upper()} ", f"bold {mode_color}"))
            else:
                parts.append((f"  {self.mode.upper()} ", mode_color))
        else:
            parts.append((f"  {self.mode.upper()} ", f"bold {mode_color}"))

        parts.append((" │ ", "dim"))

        # ── Git with animated change indicators ──
        if self.has_repo and self.git_branch:
            branch = self.git_branch
            if self.git_changes > 0:
                branch += "*"
                # Pulsing asterisk
                if (self._frame // 5) % 2 == 0:
                    branch = branch[:-1] + "◉"
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

        # ── Context with pulsing bar ──
        if self.context_pct > 0:
            pct_color = "green" if self.context_pct < 50 else "yellow" if self.context_pct < 80 else "red"
            # Pulsing percentage when active
            if self.agent_state in ("thinking", "running"):
                bar = "▓" if (self._frame // 3) % 2 == 0 else "▒"
                parts.append((f"Context {self.context_pct:.0f}%", pct_color))
            else:
                parts.append((f"Context {self.context_pct:.0f}%", pct_color))
            parts.append((" │ ", "dim"))

        # ── Session timer ──
        if self.session_start > 0:
            elapsed = int(time.time() - self.session_start)
            m, s = divmod(elapsed, 60)
            time_str = f"{m:02d}:{s:02d}"
            parts.append((f"⏱ {time_str}", "bold white"))
            parts.append((" │ ", "dim"))

        # ── Message count ──
        if self.message_count > 0:
            parts.append((f"💬 {self.message_count}", "dim"))
            parts.append((" │ ", "dim"))

        # ── Model ──
        parts.append((self.model, "bold yellow"))
        parts.append((" │ ", "dim"))

        # ── Ollama status with animated icon ──
        status_icon, status_color = self._status_style()
        # Pulsing on ok
        if self.ollama_status in ("ok", "connected") and (self._frame // 4) % 2 == 0:
            status_icon = "◉"
        parts.append((f"{status_icon} Ollama", status_color))
        parts.append((" │ ", "dim"))

        # ── Agent state with pulse ──
        state_label = self._state_label()
        state_color = {
            "ready": "green", "thinking": "cyan", "planning": "blue",
            "reading": "cyan", "editing": "yellow", "running": "yellow",
            "testing": "magenta", "reviewing": "blue", "completed": "green",
            "error": "red",
        }.get(self.agent_state, "dim")
        
        # Animated thinking dot
        if self.agent_state in ("thinking", "running", "editing", "planning", "reading"):
            dots = ["", ".", "..", "...", "..", "."]
            dot = dots[self._frame % len(dots)]
            parts.append((f"{state_label}{dot}", state_color))
        else:
            parts.append((state_label, state_color))

        # ── Response time (when available) ──
        if self.response_time > 0:
            parts.append((" │ ", "dim"))
            parts.append((f"{self.response_time:.1f}s", "dim"))

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
