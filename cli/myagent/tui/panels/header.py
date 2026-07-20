"""Premium MyAgent header with animated mascot, gradient brand, and live status.

Single-line header with:
  ✨ MYAGENT v1.0.0 │ 🤔 qwen3:8b │ Ollama ● │ ~/workspace
  (Mascot animates based on agent state)
"""

from pathlib import Path

from rich.text import Text

from ..animation import Mascot, gradient_text


class HeaderPanel:
    """Animated one-line header with mascot, brand, model, status, and workspace.
    
    Features:
      - Animated mascot character with state-based expressions
      - Gradient-colored MYAGENT brand that cycles colors
      - Ollama status with animated indicator
      - Workspace path with elision
    """

    def __init__(self):
        self.model = "qwen3:8b"
        self.ollama_status = "checking"
        self.version = "1.0.0"
        self.workspace = Path(".").resolve()
        self.mascot = Mascot()
        self._frame = 0

    def set_state(self, agent_state: str):
        """Update mascot state based on agent state."""
        self.mascot.set_state(agent_state)

    def tick(self):
        """Advance animation frames."""
        self._frame += 1
        self.mascot.tick()

    def __rich__(self) -> Text:
        self.tick()
        status_icon, status_color = self._status_style()
        ws_name = self.workspace.name if self.workspace else ""

        # Workspace path (shortened)
        ws_path = str(self.workspace)
        home = Path.home()
        try:
            ws_path = "~" + str(ws_path)[len(str(home)):] if ws_path.startswith(str(home)) else ws_path
        except Exception:
            pass
        if len(ws_path) > 25:
            ws_path = "..." + ws_path[-22:]

        # Pulsing animation for status dot
        pulse = "●" if (self._frame // 3) % 2 == 0 else "○"
        if status_icon == "●":
            status_dot = pulse
        else:
            status_dot = status_icon

        # Gradient-cycling brand name
        scheme_idx = self._frame // 60  # Change scheme every ~5 seconds at 12fps
        schemes = ["cyberpunk", "neon", "ocean", "royal"]
        scheme = schemes[scheme_idx % len(schemes)]

        brand = gradient_text(" ◆ MYAGENT ", scheme, self._frame)

        # Mascot emoji
        mascot_text = self.mascot.render_compact()

        # Model info
        model_text = Text.assemble(
            (f" {self.model} ", "bold yellow"),
        )

        # Ollama status
        status_text = Text.assemble(
            (f"· {status_dot} Ollama ", status_color),
        )

        # Workspace
        ws_text = Text.assemble(
            (f"· {ws_path}", "dim"),
        )

        # Version
        version_text = Text(f"v{self.version}", "dim")

        return Text.assemble(
            brand,
            version_text,
            (" │ ", "dim"),
            mascot_text,
            ("│ ", "dim"),
            model_text,
            (" ", ""),
            status_text,
            (" ", ""),
            ws_text,
        )

    def _status_style(self) -> tuple[str, str]:
        # Animated status indicator
        pulse = (self._frame // 4) % 2 == 0
        mapping = {
            "connected": ("●", "green"),
            "ok": ("●", "green"),
            "processing": ("◐", "yellow"),
            "warning": ("⚠", "yellow"),
            "error": ("●", "red"),
            "unavailable": ("✗", "red"),
            "checking": ("◌", "dim"),
        }
        icon, color = mapping.get(self.ollama_status, ("◌", "dim"))
        if self.ollama_status in ("ok", "connected") and pulse:
            icon = "◉"  # Pulsing indicator when all good
        return icon, color
