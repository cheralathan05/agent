"""Minimal brand header for MyAgent TUI - one line, no borders."""

from pathlib import Path

from rich.text import Text


class HeaderPanel:
    """Compact one-line header with brand, model, Ollama status, and workspace.
    
    No borders, no panels - just a clean single line of information.
    """

    def __init__(self):
        self.model = "qwen3:8b"
        self.ollama_status = "checking"
        self.version = "1.0.0"
        self.workspace = Path(".").resolve()

    def __rich__(self) -> Text:
        status_icon, status_color = self._status_style()
        ws_name = self.workspace.name if self.workspace else ""

        # Workspace path (shortened)
        ws_path = str(self.workspace)
        home = Path.home()
        try:
            ws_path = "~" + str(ws_path)[len(str(home)):] if ws_path.startswith(str(home)) else ws_path
        except Exception:
            pass
        if len(ws_path) > 30:
            ws_path = "..." + ws_path[-27:]

        return Text.assemble(
            (" ◆ MYAGENT ", "bold cyan"),
            (f"v{self.version}", "dim"),
            ("   ", ""),
            (f"{self.model}", "bold yellow"),
            (" · Ollama ", "dim"),
            (f"{status_icon}", status_color),
            ("   ", ""),
            (ws_path, "dim"),
        )

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
