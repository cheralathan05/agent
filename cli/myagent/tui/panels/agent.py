"""Agent workspace panel - the primary AI conversation area."""

import sys
from typing import Optional

from rich.console import Group, RenderableType
from rich.markdown import Markdown
from rich.text import Text


# Detect if terminal supports Unicode box-drawing characters
_SUPPORTS_UNICODE = not (
    sys.platform == "win32" and (
        "cmd" in sys.stdout.encoding or
        getattr(sys.stdout, "encoding", "").lower() in ("cp437", "cp850", "latin-1")
    )
)

if _SUPPORTS_UNICODE:
    H_TOP_L = "\u250c"   # ┌
    H_TOP_R = "\u2510"   # ┐
    H_BOT_L = "\u2514"   # └
    H_BOT_R = "\u2518"   # ┘
    H_LINE  = "\u2500"   # ─
    H_VLINE = "\u2502"   # │
else:
    H_TOP_L = "+"
    H_TOP_R = "+"
    H_BOT_L = "+"
    H_BOT_R = "+"
    H_LINE  = "-"
    H_VLINE = "|"


# Spinner frames for animated activity indicator
_SPINNER_FRAMES = ["\u25d0", "\u25d3", "\u25d1", "\u25d2"]  # ◐◓◑◒
_FALLBACK_SPINNER = ["|", "/", "-", "\\"]

if _SUPPORTS_UNICODE:
    SPINNER = _SPINNER_FRAMES
else:
    SPINNER = _FALLBACK_SPINNER


class PlanItem:
    """A single item in the agent's live plan."""

    def __init__(self, description: str, state: str = "pending"):
        self.description = description
        self.state = state  # pending, running, completed, failed

    @property
    def render(self) -> Text:
        icons = {
            "pending": ("○", "dim"),
            "running": ("●", "bold cyan"),
            "completed": ("✓", "bold green"),
            "failed": ("✗", "bold red"),
        }
        icon, style = icons.get(self.state, ("○", "dim"))
        return Text.assemble(
            (f"  {icon} ", style),
            (self.description, "white" if self.state != "pending" else "dim"),
        )


class AgentPanel:
    """Main agent workspace displaying conversation, plan, and activities.
    
    Renders without borders - just clean text layout.
    The conversation area is the primary focus.
    """

    def __init__(self):
        self.messages: list[dict] = []
        self.plans: list[PlanItem] = []
        self.activities: list[dict] = []
        self.mode = "build"
        self.agent_state = "ready"
        self.streaming_content = ""
        self.current_model = "qwen3:8b"
        self.input_text = ""
        self.show_composer = True
        self._terminal_width = 80  # Will be updated by app
        # Spinner state
        self._spinner_frame = 0

    def clear(self):
        self.messages = []
        self.plans = []
        self.activities = []
        self.streaming_content = ""

    def add_message(self, role: str, content: str):
        self.messages.append({"role": role, "content": content})

    def set_streaming(self, content: str):
        self.streaming_content = content

    def add_activity(self, icon: str, text: str, style: str = "dim"):
        self.activities.append({"icon": icon, "text": text, "style": style})
        if len(self.activities) > 50:
            self.activities.pop(0)

    def add_plan(self, description: str, state: str = "pending"):
        self.plans.append(PlanItem(description, state))

    def update_plan(self, index: int, state: str):
        if 0 <= index < len(self.plans):
            self.plans[index].state = state

    def tick_spinner(self):
        """Advance the spinner animation by one frame."""
        self._spinner_frame = (self._spinner_frame + 1) % len(SPINNER)

    def get_mode_display(self) -> str:
        labels = {
            "plan": "PLAN", "build": "BUILD", "debug": "DEBUG",
            "review": "REVIEW", "ask": "ASK",
        }
        return labels.get(self.mode, "BUILD")

    def __rich__(self) -> RenderableType:
        elements = []

        # ── Mode header line ──
        mode_color = {
            "plan": "blue", "build": "cyan", "debug": "magenta",
            "review": "yellow", "ask": "green",
        }.get(self.mode, "white")

        mode_line = Text.assemble(
            ("  ", ""),
            (f"{self.get_mode_display()}", f"bold {mode_color}"),
            (" │ ", "dim"),
            self._state_renderable(),
        )
        elements.append(mode_line)

        # ── Plan section ──
        if self.plans:
            elements.append(Text(""))
            # Plan header
            elements.append(Text(f"  {H_LINE * 5} Plan {H_LINE * 25}", "dim"))
            for p in self.plans:
                elements.append(p.render)

        # ── Activities (tool calls) ──
        if self.activities:
            recent = self.activities[-10:]
            elements.append(Text(""))
            for a in recent:
                icon = a["icon"]
                text = a["text"]
                style = a["style"]
                elements.append(Text.assemble(
                    ("  ", ""),
                    (f"{icon} ", style),
                    (text, style),
                ))

        # ── Conversation messages ──
        if self.messages:
            elements.append(Text(""))
            for msg in self.messages[-8:]:
                if msg["role"] == "user":
                    elements.append(self._render_user_message(msg["content"]))
                elif msg["role"] == "assistant":
                    elements.append(self._render_assistant_message(msg["content"]))

        # ── Streaming content ──
        if self.streaming_content:
            elements.append(self._render_assistant_message(self.streaming_content, streaming=True))

        # ── Empty state ──
        if not self.messages and not self.plans and not self.streaming_content:
            elements.append(Text(""))
            elements.append(Text(""))
            elements.append(Text("  ◆ MYAGENT", "bold cyan"))
            elements.append(Text("  AI Software Engineering Agent", "dim"))
            elements.append(Text(""))
            elements.append(Text("  What would you like to build?", "white"))
            elements.append(Text(""))
            elements.append(Text("  Try: 'Analyze this project' or 'Build a feature'", "italic dim"))
            elements.append(Text("  Use /help to see available commands", "italic dim"))

        return Group(*elements)

    def _state_renderable(self) -> Text:
        # Use animated spinner for active states
        if self.agent_state in ("thinking", "planning", "reading", "editing",
                                 "running", "testing", "reviewing", "waiting_approval"):
            spinner = SPINNER[self._spinner_frame]
            labels = {
                "thinking": "Thinking", "planning": "Planning",
                "reading": "Reading", "editing": "Editing",
                "running": "Working", "testing": "Testing",
                "reviewing": "Reviewing", "waiting_approval": "Waiting",
            }
            label = labels.get(self.agent_state, "Working")
            return Text.assemble(
                (f"{spinner} ", "bold cyan"),
                (label, "cyan"),
            )
        else:
            state_styles = {
                "ready": ("● Ready", "green"),
                "completed": ("✓ Completed", "green"),
                "error": ("✗ Error", "red"),
            }
            label, style = state_styles.get(self.agent_state, ("● Idle", "dim"))
            return Text(f"{label}", style=style)

    def _render_user_message(self, content: str) -> Group:
        """Render a user message compactly without borders."""
        display = content[:300] + ("..." if len(content) > 300 else "")
        # Truncate to first few lines
        lines = display.split("\n")
        if len(lines) > 5:
            display = "\n".join(lines[:5]) + "\n..."
        return Group(
            Text(f"  {H_LINE * 42}", "dim"),
            Text.assemble(
                ("  You", "bold green"),
            ),
            Text(f"  {display}", "white"),
        )

    def _render_assistant_message(self, content: str, streaming: bool = False) -> Group:
        """Render an assistant message without borders, with Markdown support."""
        display = content
        # For non-streaming, truncate very long messages
        if not streaming and len(content) > 800:
            display = content[:800] + "\n\n... (truncated)"

        title = "MyAgent" if not streaming else f"{SPINNER[self._spinner_frame]} MyAgent"

        # Render as Markdown if it contains markdown-like syntax, else plain text
        has_markdown = any(marker in content for marker in ("#", "```", "- ", "* ", "1. ", "**"))
        body = Markdown(display) if has_markdown else Text(display)

        return Group(
            Text(""),
            Text.assemble(
                ("  ", ""),
                (f"{title}", "bold cyan"),
            ),
            Text(""),
            body,
        )

    def render_composer(self) -> Group:
        """Render the input composer area at the bottom of the agent panel."""
        # Calculate dynamic box width based on terminal width
        box_width = max(30, min(72, self._terminal_width - 8))
        prompt_max = box_width - 4

        # Active mode tags
        mode_colors = {
            "build": "cyan", "plan": "blue", "debug": "magenta", "review": "yellow",
        }
        modes = ["Build", "Plan", "Debug", "Review"]
        mode_tags = []
        for m in modes:
            color = mode_colors.get(m.lower(), "white")
            if m.lower() == self.mode:
                mode_tags.append((f"[{m}]", f"bold {color}"))
            else:
                mode_tags.append((f"{m}", "dim"))

        mode_line = Text.assemble(*mode_tags)

        # Prompt text (truncated to fit)
        prompt = self.input_text if self.input_text else "Ask MyAgent to build, fix, debug, or explain..."
        if len(prompt) > prompt_max:
            prompt = prompt[:prompt_max - 3] + "..."
        prompt_style = "white" if self.input_text else "dim italic"

        # Pad mode line to balance width with model info
        mode_str = " ".join(t[0].strip() for t in mode_tags)
        right_info = f"{self.current_model}  Ctrl+Enter"
        pad = max(0, box_width - len(mode_str) - len(right_info) - 4)

        composer_lines = [
            Text.assemble(
                (f"  {H_TOP_L}", "dim"),
                (f"{H_LINE * box_width}", "dim"),
                (f"{H_TOP_R}", "dim"),
            ),
            Text.assemble(
                (f"  {H_VLINE} ", "dim"),
                (prompt, prompt_style),
                (f"{' ' * max(0, box_width - len(prompt))} {H_VLINE}", "dim"),
            ),
            Text.assemble(
                (f"  {H_BOT_L}", "dim"),
                (f"{H_LINE * box_width}", "dim"),
                (f"{H_BOT_R}", "dim"),
            ),
        ]

        # Mode + model info line below composer
        info_line = Text.assemble(
            ("   ", ""),
            mode_line,
            (" " * pad, ""),
            (f"{self.current_model}", "bold yellow"),
            ("  Ctrl+Enter", "dim"),
        )

        return Group(*composer_lines, info_line)
