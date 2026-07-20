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
        self.input_cursor_row = 0       # Cursor row within input
        self.input_cursor_col = 0       # Cursor col within input
        self._input_lines: list[str] = []  # Multiline buffer for display
        self._is_typing = False         # Whether user is actively typing
        self._cursor_visible = True     # Blinking cursor toggle
        self._terminal_width = 80       # Updated by app on resize
        self._terminal_height = 24      # Updated by app on resize
        # Spinner state
        self._spinner_frame = 0

    def clear(self):
        self.messages = []
        self.plans = []
        self.activities = []
        self.streaming_content = ""
        self.input_text = ""
        self._input_lines = []

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

    def _tick_cursor(self):
        """Toggle cursor visibility for blinking effect (called periodically)."""
        self._cursor_visible = not self._cursor_visible

    def _cursor_char(self) -> str:
        """Return a cursor character (block or pipe depending on visibility)."""
        if not self._is_typing:
            return ""
        return "\u2588" if self._cursor_visible else " "  # █ or space

    def render_composer(self) -> Group:
        """Render the input composer area as a standalone renderable.
        
        - When agent is thinking/working: shows an animated thinking indicator
          with spinner, state label, and cancel hint.
        - When agent is idle/ready: shows the interactive input box
          with blinking cursor, multiline support, and active/inactive states.
        """
        # Check if agent is in an active working state
        active_states = {
            "thinking", "planning", "reading", "editing",
            "running", "testing", "reviewing", "waiting_approval",
        }
        if self.agent_state in active_states:
            return self._render_thinking()

        is_compact = self._terminal_height < 15
        if is_compact:
            return self._render_compact()
        return self._render_full()

    def _render_thinking(self) -> Group:
        """Render an animated thinking indicator while agent is working.
        
        Shows a live spinner with the current state label, model info,
        and a cancel hint. Adapts to compact mode on small terminals.
        """
        spinner = SPINNER[self._spinner_frame]
        is_compact = self._terminal_height < 15
        box_width = max(30, min(72, self._terminal_width - 8))
        content_width = box_width - 2

        # State label (human-readable)
        state_labels = {
            "thinking": "Thinking",
            "planning": "Planning",
            "reading": "Reading project",
            "editing": "Editing files",
            "running": "Working",
            "testing": "Testing",
            "reviewing": "Reviewing",
            "waiting_approval": "Waiting for approval",
        }
        state_label = state_labels.get(self.agent_state, "Working")

        # Animated sub-status messages that rotate during thinking
        thinking_messages = [
            "Processing your request...",
            "Analyzing the codebase...",
            "Generating solution...",
            "Working on it...",
            "Almost there...",
        ]
        msg_idx = self._spinner_frame % len(thinking_messages)
        status_msg = thinking_messages[msg_idx]

        if is_compact:
            # ── Compact thinking indicator (2 lines) ──
            return Group(
                Text.assemble(
                    ("  ", ""),
                    (f"{spinner} ", "bold cyan"),
                    (f"{state_label}...", "cyan"),
                ),
                Text.assemble(
                    ("   ", ""),
                    (f"{self.current_model}", "bold yellow"),
                    (" · ", "dim"),
                    ("Ctrl+C", "dim"),
                    (" to cancel", "dim"),
                ),
            )

        # ── Full thinking indicator with box ──
        # Line 1 content: spinner + state_label + "..."
        line1_text = f"{spinner} {state_label}..."
        # Line 2 content: status message with 2-space indent
        line2_text = f"  {status_msg}"
        # Line 3 content: cancel hint
        line3_text = "Press Ctrl+C to cancel"

        lines = [
            # Top border
            Text.assemble(
                (f"  {H_TOP_L}", "dim"),
                (f"{H_LINE * content_width}", "dim"),
                (f"{H_TOP_R}", "dim"),
            ),
            # Line 1: Spinner + state label
            Text.assemble(
                (f"  {H_VLINE} ", "dim"),
                (line1_text, "bold cyan"),
                (f" {' ' * max(0, content_width - len(line1_text))} {H_VLINE}", "dim"),
            ),
            # Line 2: Status message + model
            Text.assemble(
                (f"  {H_VLINE} ", "dim"),
                (line2_text, "dim"),
                (f" {' ' * max(0, content_width - len(line2_text))} {H_VLINE}", "dim"),
            ),
            # Line 3: Cancel hint
            Text.assemble(
                (f"  {H_VLINE} ", "dim"),
                (line3_text, "italic dim"),
                (f" {' ' * max(0, content_width - len(line3_text))} {H_VLINE}", "dim"),
            ),
            # Bottom border
            Text.assemble(
                (f"  {H_BOT_L}", "dim"),
                (f"{H_LINE * content_width}", "dim"),
                (f"{H_BOT_R}", "dim"),
            ),
        ]

        # Info line below
        mode_color = {
            "build": "cyan", "plan": "blue", "debug": "magenta",
            "review": "yellow", "ask": "green",
        }.get(self.mode, "white")
        mode_tag = Text.assemble(
            (f"[{self.get_mode_display()}]", f"bold {mode_color}"),
        )
        # Animated state indicator in status bar
        status = Text.assemble(
            (f"{spinner} ", "bold cyan"),
            (f"{state_label.lower()}", "cyan"),
        )

        left_info = f" [{self.get_mode_display()}]  {spinner} {state_label.lower()}"
        right_info = f"{self.current_model}  Ctrl+C"
        pad = max(4, box_width - 2 - len(left_info) - len(right_info))

        info_line = Text.assemble(
            ("   ", ""),
            mode_tag,
            ("  ", ""),
            status,
            (" " * pad, ""),
            (f"{self.current_model}", "bold yellow"),
            ("  Ctrl+C", "dim"),
        )

        return Group(*lines, info_line)

    def _render_compact(self) -> Group:
        """Compact 2-line composer for short terminals."""
        prompt = self.input_text if self.input_text else "Ask MyAgent..."
        cursor = self._cursor_char() if self._is_typing else ""
        display = self.input_text + cursor if self.input_text else ""
        return Group(
            Text.assemble(
                ("  ", ""),
                ("▸ ", "bold cyan"),
                (display if self.input_text else "Ask MyAgent...",
                 "white" if self.input_text else "dim italic"),
            ),
            Text.assemble(
                ("   ", ""),
                (f"[{self.get_mode_display()}]", "dim"),
                (f"  {self.current_model} ", "dim"),
                (f"{'typing' if self._is_typing else 'ready'}", "green" if self._is_typing else "dim"),
            ),
        )

    def _render_full(self) -> Group:
        """Full-size multi-line composer with box and cursor."""
        box_width = max(30, min(72, self._terminal_width - 8))
        content_width = box_width - 2  # Space between │ walls

        # ── Parse input lines ──
        input_lines = self.input_text.split("\n") if self.input_text else [""]

        cursor_row = self.input_cursor_row
        cursor_col = self.input_cursor_col

        # ── Determine visible scroll window ──
        max_display_lines = 3
        total_lines = len(input_lines)
        if total_lines <= max_display_lines:
            start_line = 0
        else:
            start_line = max(0, min(
                cursor_row - 1,
                total_lines - max_display_lines
            ))

        visible_lines = input_lines[start_line:start_line + max_display_lines]
        while len(visible_lines) < max_display_lines:
            visible_lines.append("")

        # ── Cursor ──
        cursor_ch = self._cursor_char()
        has_content = bool(self.input_text)

        # ── Build box ──
        lines = [
            Text.assemble(
                (f"  {H_TOP_L}", "dim"),
                (f"{H_LINE * content_width}", "dim"),
                (f"{H_TOP_R}", "dim"),
            )
        ]

        # Content lines
        for i, line in enumerate(visible_lines):
            abs_idx = start_line + i
            is_cursor_line = abs_idx == cursor_row
            display_line = line[:content_width]

            if not has_content and i == 0:
                # Empty buffer - show the placeholder on first line
                if is_cursor_line and cursor_ch:
                    lines.append(Text.assemble(
                        (f"  {H_VLINE} ", "dim"),
                        (cursor_ch, "bold cyan"),
                        ("Ask MyAgent to build, fix, debug, or explain...", "dim italic"),
                        (f" {' ' * max(0, content_width - 1 - 46)} {H_VLINE}", "dim"),
                    ))
                else:
                    lines.append(Text.assemble(
                        (f"  {H_VLINE} ", "dim"),
                        ("Ask MyAgent to build, fix, debug, or explain...", "dim italic"),
                        (f" {' ' * max(0, content_width - 46)} {H_VLINE}", "dim"),
                    ))
                # Remaining lines are blank
                continue

            if is_cursor_line and cursor_ch:
                # Show cursor within text
                before = display_line[:cursor_col]
                at_cursor = display_line[cursor_col:cursor_col + 1] if cursor_col < len(display_line) else " "
                after = display_line[cursor_col + 1:] if cursor_col < len(display_line) else ""
                line_content = before + cursor_ch + at_cursor + after
                if len(line_content) > content_width:
                    line_content = line_content[:content_width]
                lines.append(Text.assemble(
                    (f"  {H_VLINE} ", "dim"),
                    (line_content, "white"),
                    (f" {' ' * max(0, content_width - len(line_content))} {H_VLINE}", "dim"),
                ))
            else:
                visible_text = display_line + (" " if is_cursor_line and not cursor_ch else "")
                lines.append(Text.assemble(
                    (f"  {H_VLINE} ", "dim"),
                    (visible_text, "white"),
                    (f" {' ' * max(0, content_width - len(visible_text))} {H_VLINE}", "dim"),
                ))

        # Bottom border
        lines.append(Text.assemble(
            (f"  {H_BOT_L}", "dim"),
            (f"{H_LINE * content_width}", "dim"),
            (f"{H_BOT_R}", "dim"),
        ))

        # Scroll indicator
        scroll_info = ""
        if total_lines > max_display_lines:
            scroll_info = f"{start_line + 1}-{min(start_line + max_display_lines, total_lines)}/{total_lines}"

        # ── Info line below composer ──
        mode_color = {
            "build": "cyan", "plan": "blue", "debug": "magenta",
            "review": "yellow", "ask": "green",
        }.get(self.mode, "white")
        mode_tag = Text.assemble(
            (f"[{self.get_mode_display()}]", f"bold {mode_color}"),
        )
        status = Text.assemble(
            ("● ", "green" if self._is_typing else "dim"),
            ("typing" if self._is_typing else "ready", "green" if self._is_typing else "dim"),
        )

        # Calculate padding for right-aligned model/kbd info
        left_info = f" [{self.get_mode_display()}]  \u25cf {'typing' if self._is_typing else 'ready'}"
        if scroll_info:
            left_info += f"  {scroll_info}"
        right_info = f"{self.current_model}  Enter \u00b7 Shift+Enter"
        pad = max(4, box_width - 2 - len(left_info) - len(right_info))

        info_line = Text.assemble(
            ("   ", ""),
            mode_tag,
            ("  ", ""),
            status,
            (" " * pad, ""),
            (scroll_info + "  " if scroll_info else "", "dim"),
            (f"{self.current_model}", "bold yellow"),
            ("  Enter", "dim"),
            (" \u00b7 ", "dim"),
            ("Shift+Enter", "dim"),
        )

        return Group(*lines, info_line)
