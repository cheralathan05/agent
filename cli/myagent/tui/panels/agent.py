"""Premium Agent workspace panel - the primary AI conversation area with animations.

Features:
  - Rich message bubbles for user/assistant messages
  - Typewriter streaming effect
  - Animated thinking indicator with pulsating progress
  - Welcome screen with particle sparkles
  - Enhanced code rendering with language badges
  - Mode display with gradient colors
"""

import sys
from typing import Optional

from rich.console import Group, RenderableType
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.text import Text

from ..animation import (
    SparkleManager, AnimatedBar, gradient_text,
    pulsing_style, _SUPPORTS_UNICODE
)


# ── Box-drawing characters ────────────────────────

if _SUPPORTS_UNICODE:
    H_TOP_L = "┌"
    H_TOP_R = "┐"
    H_BOT_L = "└"
    H_BOT_R = "┘"
    H_LINE  = "─"
    H_VLINE = "│"
else:
    H_TOP_L = "+"
    H_TOP_R = "+"
    H_BOT_L = "+"
    H_BOT_R = "+"
    H_LINE  = "-"
    H_VLINE = "|"


# ── Spinner frames ────────────────────────────────

_SPINNER_FRAMES = ["◐", "◓", "◑", "◒"]
_FALLBACK_SPINNER = ["|", "/", "-", "\\"]
if _SUPPORTS_UNICODE:
    SPINNER = _SPINNER_FRAMES
else:
    SPINNER = _FALLBACK_SPINNER

# Pulsing frames for thinking animation
_PULSE_FRAMES = ["·", "•", "●", "○", "•", "·"]
_THINKING_DOTS = ["", ".", "..", "...", "..", "."]

# Color schemes for mode display
_MODE_SCHEMES = {
    "plan":   "blue",
    "build":  "cyan",
    "debug":  "magenta",
    "review": "yellow",
    "ask":    "green",
}


class PlanItem:
    """A single item in the agent's live plan with enhanced styling."""

    def __init__(self, description: str, state: str = "pending"):
        self.description = description
        self.state = state

    @property
    def render(self) -> Text:
        icons = {
            "pending":   ("○", "dim"),
            "running":   ("●", "bold cyan"),
            "completed": ("✓", "bold green"),
            "failed":    ("✗", "bold red"),
        }
        icon, style = icons.get(self.state, ("○", "dim"))
        return Text.assemble(
            (f"  {icon} ", style),
            (self.description, "white" if self.state != "pending" else "dim"),
        )


class AgentPanel:
    """Premium agent workspace with full animation support."""

    def __init__(self):
        self.messages: list[dict] = []
        self.plans: list[PlanItem] = []
        self.activities: list[dict] = []
        self.mode = "build"
        self.agent_state = "ready"
        self.streaming_content = ""
        self.current_model = "qwen3:8b"
        self.token_count = 0
        self.response_time = 0.0
        
        # Input state
        self.input_text = ""
        self.input_cursor_row = 0
        self.input_cursor_col = 0
        self._input_lines: list[str] = []
        self._is_typing = False
        self._cursor_visible = True
        
        # Terminal dimensions
        self._terminal_width = 80
        self._terminal_height = 24
        
        # Animation state
        self._spinner_frame = 0
        self._pulse_frame = 0
        self._thinking_dot_frame = 0
        self._sparkles = SparkleManager(12)
        self._welcome_frame = 0
        self._fade_counter = 0
        
        # Session stats
        self.session_message_count = 0

    # ── State management ──

    def clear(self):
        self.messages = []
        self.plans = []
        self.activities = []
        self.streaming_content = ""
        self.input_text = ""
        self._input_lines = []
        self.token_count = 0
        self.session_message_count = 0
        self._sparkles = SparkleManager(12)

    def add_message(self, role: str, content: str):
        self.messages.append({"role": role, "content": content})
        self.session_message_count += 1

    def set_streaming(self, content: str):
        self.streaming_content = content

    def add_activity(self, icon: str, text: str, style: str = "dim"):
        self.activities.append({"icon": icon, "text": text, "style": style})
        if len(self.activities) > 50:
            self.activities.pop(0)
        # Sparkle burst on new activity
        if icon in ("✓", "●", "✦"):
            self._sparkles.add_burst(3, 0, 2)

    def add_plan(self, description: str, state: str = "pending"):
        self.plans.append(PlanItem(description, state))

    def update_plan(self, index: int, state: str):
        if 0 <= index < len(self.plans):
            old_state = self.plans[index].state
            self.plans[index].state = state
            # Sparkle on completion
            if old_state != "completed" and state == "completed":
                self._sparkles.add_burst(5, 0, 3)

    def tick_spinner(self):
        """Advance spinner and pulse animations."""
        self._spinner_frame = (self._spinner_frame + 1) % len(SPINNER)
        self._pulse_frame = (self._pulse_frame + 1) % len(_PULSE_FRAMES)
        self._thinking_dot_frame = (self._thinking_dot_frame + 1) % len(_THINKING_DOTS)
        self._sparkles.tick()
        self._welcome_frame += 1

    def get_mode_display(self) -> str:
        labels = {
            "plan": "PLAN", "build": "BUILD", "debug": "DEBUG",
            "review": "REVIEW", "ask": "ASK",
        }
        return labels.get(self.mode, "BUILD")

    # ── Main render ──

    def __rich__(self) -> RenderableType:
        elements = []

        # ── Mode header line with gradient ──
        mode_color = _MODE_SCHEMES.get(self.mode, "white")
        # Cycle through colors slowly for a breathing effect
        scheme_idx = self._welcome_frame // 120
        schemes = ["cyberpunk", "neon", "ocean"]
        scheme = schemes[scheme_idx % len(schemes)]
        
        mode_brand = gradient_text(f"  ◆ {self.get_mode_display()}", scheme, self._welcome_frame)

        elements.append(Text.assemble(
            mode_brand,
            (" │ ", "dim"),
            self._state_renderable(),
        ))

        # ── Plan section with animated header ──
        if self.plans:
            elements.append(Text(""))
            pulse_ch = _PULSE_FRAMES[self._pulse_frame] if any(p.state == "running" for p in self.plans) else "─"
            elements.append(Text(f"  {H_LINE * 3} {pulse_ch} Plan {pulse_ch} {H_LINE * 20}", "dim"))
            for p in self.plans:
                elements.append(p.render)
            elements.append(Text(f"  {H_LINE * 30}", "dim"))

        # ── Activities (tool calls) with sparkles ──
        if self.activities:
            recent = self.activities[-10:]
            elements.append(Text(""))
            for a in recent:
                icon = a["icon"]
                text = a["text"]
                style = a["style"]
                # Animated sparkle dot for certain activities
                if icon in ("✓", "●", "✦"):
                    icon = f"{_PULSE_FRAMES[self._pulse_frame]}" if icon == "●" else icon
                elements.append(Text.assemble(
                    ("  ", ""),
                    (f"{icon} ", style),
                    (text, style),
                ))

        # ── Conversation messages ──
        if self.messages:
            elements.append(Text(""))
            for msg in self.messages[-6:]:
                if msg["role"] == "user":
                    elements.append(self._render_user_message(msg["content"]))
                elif msg["role"] == "assistant":
                    elements.append(self._render_assistant_message(msg["content"]))

        # ── Streaming content ──
        if self.streaming_content:
            elements.append(self._render_assistant_message(
                self.streaming_content, streaming=True
            ))

        # ── Sparkle overlays ──
        if self._sparkles.has_particles:
            for s in self._sparkles.render_all():
                elements.append(s)

        # ── Welcome screen ──
        if not self.messages and not self.plans and not self.streaming_content:
            elements.append(self._render_welcome())

        return Group(*elements)

    # ── State renderer with animation ──

    def _state_renderable(self) -> Text:
        if self.agent_state in ("thinking", "planning", "reading", "editing",
                                 "running", "testing", "reviewing", "waiting_approval"):
            spinner = SPINNER[self._spinner_frame]
            dots = _THINKING_DOTS[self._thinking_dot_frame]
            labels = {
                "thinking": "Thinking", "planning": "Planning",
                "reading": "Reading", "editing": "Editing",
                "running": "Working", "testing": "Testing",
                "reviewing": "Reviewing", "waiting_approval": "Waiting",
            }
            label = labels.get(self.agent_state, "Working")
            pulse_style = pulsing_style(self._welcome_frame, "cyan", 0.08)
            return Text.assemble(
                (f"{spinner} ", "bold cyan"),
                (f"{label}{dots}", pulse_style),
            )
        else:
            state_styles = {
                "ready":     ("● Ready", "green"),
                "completed": ("✓ Completed", "green"),
                "error":     ("✗ Error", "red"),
            }
            label, style = state_styles.get(self.agent_state, ("● Idle", "dim"))
            return Text(f"{label}", style=style)

    # ── Message renderers ──

    def _render_user_message(self, content: str) -> Group:
        """Render a user message with a styled bubble."""
        display = content[:300] + ("..." if len(content) > 300 else "")
        lines = display.split("\n")
        if len(lines) > 5:
            display = "\n".join(lines[:5]) + "\n..."

        # Create a subtle user bubble
        return Group(
            Text(""),
            Text.assemble(
                ("  ┌── ", "dim"),
                ("You", "bold green"),
                (" ──" + "─" * max(2, 30 - len(display[:40])), "dim"),
            ),
            Text(f"  │ {display}", "white"),
            Text(f"  └{'─' * min(45, len(display[:50]) + 2)}", "dim"),
        )

    def _render_assistant_message(self, content: str, streaming: bool = False) -> Group:
        """Render assistant message with enhanced code blocks and streaming indicator."""
        display = content
        if not streaming and len(content) > 800:
            display = content[:800] + "\n\n... (truncated)"

        if streaming:
            title = Text.assemble(
                (f"{SPINNER[self._spinner_frame]} ", "bold cyan"),
                ("MyAgent", "bold cyan"),
            )
        else:
            title = Text.assemble(
                ("◆ ", "bold cyan"),
                ("MyAgent", "bold cyan"),
            )

        # Check for code blocks - render with syntax highlighting
        if "```" in content:
            return Group(
                Text(""),
                title,
                Text(""),
                self._render_with_code_blocks(display, streaming),
            )

        # Simple content
        has_markdown = any(marker in content for marker in ("#", "- ", "* ", "1. ", "**"))
        if has_markdown:
            body = Markdown(display)
        else:
            body = Text(display)

        return Group(
            Text(""),
            title,
            Text(""),
            Text(f"  {display}", "white") if not has_markdown else body,
        )

    def _render_with_code_blocks(self, content: str, streaming: bool) -> Group:
        """Split content by code blocks and render each part appropriately."""
        elements = []
        parts = content.split("```")
        
        for i, part in enumerate(parts):
            if i % 2 == 0:
                # Plain text
                if part.strip():
                    if any(m in part for m in ("#", "- ", "* ", "1. ", "**")):
                        elements.append(Markdown(part.strip()))
                    else:
                        elements.append(Text(f"  {part.strip()}"))
            else:
                # Code block
                lines = part.split("\n")
                lang = lines[0].strip() if lines else ""
                code = "\n".join(lines[1:]) if len(lines) > 1 else part
                if streaming or len(code) > 1000:
                    # During streaming or large blocks, show as text to avoid re-parsing
                    elements.append(Text(f"  ```{lang}"))
                    for cl in code.split("\n"):
                        elements.append(Text(f"  {cl}"))
                    elements.append(Text("  ```"))
                else:
                    try:
                        syntax = Syntax(code, lang or "python", theme="monokai", line_numbers=True)
                        lang_badge = Text(f" [{lang}] ", style="bold dim")
                        elements.append(lang_badge)
                        elements.append(syntax)
                    except Exception:
                        elements.append(Text(f"  {code}"))

        return Group(*elements)

    # ── Welcome screen with animations ──

    def _render_welcome(self) -> Group:
        """Animated welcome screen with sparkle effects."""
        elements = []
        elements.append(Text(""))
        elements.append(Text(""))

        # Animated MYAGENT brand with gradient
        schemes = ["cyberpunk", "neon", "ocean", "royal"]
        scheme = schemes[(self._welcome_frame // 60) % len(schemes)]
        brand = gradient_text("  ◆  M Y A G E N T  ◆  ", scheme, self._welcome_frame, bold=True)
        elements.append(brand)

        # Subtitle with pulsing effect
        pulse_style = pulsing_style(self._welcome_frame, "cyan", 0.06)
        elements.append(Text(f"  AI Software Engineering Agent", style=pulse_style))

        elements.append(Text(""))

        # Animated tagline with typewriter-like reveal
        tag = "  What would you like to build today?"
        reveal = min(len(tag), self._welcome_frame // 2)
        if reveal > 0:
            elements.append(Text(tag[:reveal], "white"))

        elements.append(Text(""))

        # Help hints with sparkle
        hints = [
            ("  ✦ ", "bold cyan"),
            ("Try 'Analyze this project'", "italic dim"),
            (" or ", "dim"),
            ("'Build a feature'", "italic dim"),
        ]
        elements.append(Text.assemble(*hints))

        elements.append(Text.assemble(
            ("  ✦ ", "bold cyan"),
            ("Use /help to see commands", "italic dim"),
        ))

        # Sparkle burst periodically on welcome
        if self._welcome_frame % 30 == 0:
            self._sparkles.add_burst(10, 0, 2)
        for s in self._sparkles.render_all():
            elements.append(Text(f"   {s}"))

        return Group(*elements)

    # ── Cursor ──

    def _tick_cursor(self):
        self._cursor_visible = not self._cursor_visible

    def _cursor_char(self) -> str:
        if not self._is_typing:
            return ""
        return "█" if self._cursor_visible else " "

    # ── Composer / Input area ──

    def render_composer(self, turn_count: int = 0) -> Group:
        """Render the input composer with thinking indicator or input box.
        
        Args:
            turn_count: Current conversation turn number (0-based).
        """
        active_states = {
            "thinking", "planning", "reading", "editing",
            "running", "testing", "reviewing", "waiting_approval",
        }
        if self.agent_state in active_states:
            return self._render_thinking()

        is_compact = self._terminal_height < 15
        if is_compact:
            return self._render_compact(turn_count)
        return self._render_full(turn_count)

    def _render_thinking(self) -> Group:
        """Animated thinking indicator with pulsing progress visualization."""
        spinner = SPINNER[self._spinner_frame]
        is_compact = self._terminal_height < 15
        box_width = max(30, min(72, self._terminal_width - 8))
        content_width = box_width - 2

        state_labels = {
            "thinking": "Thinking", "planning": "Planning",
            "reading": "Reading project", "editing": "Editing files",
            "running": "Working", "testing": "Testing",
            "reviewing": "Reviewing", "waiting_approval": "Waiting for approval",
        }
        state_label = state_labels.get(self.agent_state, "Working")

        # Animated sub-status messages
        thinking_messages = [
            "Processing your request",
            "Analyzing the codebase",
            "Generating solution",
            "Working on it",
            "Almost there",
        ]
        msg_idx = self._spinner_frame % len(thinking_messages)
        status_msg = thinking_messages[msg_idx]

        # Simulated progress bar that pulses
        progress_pct = min(95, (self._spinner_frame * 7) % 100)
        bar = AnimatedBar(8)
        bar.tick()
        bar_render = bar.render(progress_pct, pulse=True)

        dots = _THINKING_DOTS[self._thinking_dot_frame]

        if is_compact:
            return Group(
                Text.assemble(
                    ("  ", ""),
                    (f"{spinner} ", "bold cyan"),
                    (f"{state_label}{dots}", "cyan"),
                ),
                Text.assemble(
                    ("   ", ""),
                    (f"{self.current_model}", "bold yellow"),
                    (" · ", "dim"),
                    ("Ctrl+C", "dim"),
                    (" to cancel", "dim"),
                ),
            )

        # Full thinking indicator with animated bar
        line1_text = f"{spinner}  {state_label}{dots}"
        line2_text = f"  {status_msg}{dots}"
        line3_left = "  "
        line3_bar = bar_render
        line3_right = ""
        cancel_text = "Press Ctrl+C to cancel"

        lines = [
            Text.assemble(
                (f"  {H_TOP_L}", "dim"),
                (f"{H_LINE * content_width}", "dim"),
                (f"{H_TOP_R}", "dim"),
            ),
            Text.assemble(
                (f"  {H_VLINE} ", "dim"),
                (line1_text, "bold cyan"),
                (f" {' ' * max(0, content_width - len(line1_text))} {H_VLINE}", "dim"),
            ),
            Text.assemble(
                (f"  {H_VLINE} ", "dim"),
                (line2_text, "dim"),
                (f" {' ' * max(0, content_width - len(line2_text))} {H_VLINE}", "dim"),
            ),
            Text.assemble(
                (f"  {H_VLINE} ", "dim"),
                (bar_render, ""),
                (f" {' ' * max(0, content_width - 8)}", "dim"),
                (f" {cancel_text}", "italic dim"),
                (f" {' ' * max(0, content_width - len(cancel_text) - 10)} {H_VLINE}", "dim"),
            ),
            Text.assemble(
                (f"  {H_BOT_L}", "dim"),
                (f"{H_LINE * content_width}", "dim"),
                (f"{H_BOT_R}", "dim"),
            ),
        ]

        # Info line
        mode_color = _MODE_SCHEMES.get(self.mode, "white")
        mode_tag = Text.assemble((f"[{self.get_mode_display()}]", f"bold {mode_color}"))
        status = Text.assemble(
            (f"{spinner} ", "bold cyan"),
            (f"{state_label.lower()}", "cyan"),
        )

        left_info = f" [{self.get_mode_display()}]  {spinner} {state_label.lower()}"
        right_info = f"{self.current_model}  Ctrl+C"
        pad = max(4, box_width - 2 - len(left_info) - len(right_info))

        info_line = Text.assemble(
            ("   ", ""), mode_tag, ("  ", ""), status,
            (" " * pad, ""),
            (f"{self.current_model}", "bold yellow"),
            ("  Ctrl+C", "dim"),
        )

        return Group(*lines, info_line)

    def _render_compact(self, turn_count: int = 0) -> Group:
        """Compact input composer with turn context."""
        prompt = self.input_text if self.input_text else "Ask MyAgent..."
        cursor = self._cursor_char() if self._is_typing else ""
        display = (prompt + cursor) if self.input_text else prompt
        dots = _THINKING_DOTS[self._thinking_dot_frame] if self._is_typing else ""
        
        # Show turn count if conversation is active
        context_hint = f" #{turn_count}" if turn_count > 0 else ""
        
        return Group(
            Text.assemble(
                ("  ", ""),
                ("▸ ", "bold cyan"),
                (display, "white" if self.input_text else "dim italic"),
            ),
            Text.assemble(
                ("   ", ""),
                (f"[{self.get_mode_display()}]", "dim"),
                (f"{context_hint}", "green"),
                (f"  {self.current_model} ", "dim"),
                (f"{'typing' + dots if self._is_typing else 'ready'}", "green" if self._is_typing else "dim"),
            ),
        )

    def _render_full(self, turn_count: int = 0) -> Group:
        """Full-size multi-line composer with box, animated cursor, and conversation context.
        
        Args:
            turn_count: Current conversation turn number.
        """
        box_width = max(30, min(72, self._terminal_width - 8))
        content_width = box_width - 2

        input_lines = self.input_text.split("\n") if self.input_text else [""]
        cursor_row = self.input_cursor_row
        cursor_col = self.input_cursor_col

        max_display_lines = 3
        total_lines = len(input_lines)
        if total_lines <= max_display_lines:
            start_line = 0
        else:
            start_line = max(0, min(cursor_row - 1, total_lines - max_display_lines))

        visible_lines = input_lines[start_line:start_line + max_display_lines]
        while len(visible_lines) < max_display_lines:
            visible_lines.append("")

        cursor_ch = self._cursor_char()
        has_content = bool(self.input_text)

        lines = [
            Text.assemble(
                (f"  {H_TOP_L}", "dim"),
                (f"{H_LINE * content_width}", "dim"),
                (f"{H_TOP_R}", "dim"),
            )
        ]

        for i, line in enumerate(visible_lines):
            abs_idx = start_line + i
            is_cursor_line = abs_idx == cursor_row
            display_line = line[:content_width]

            if not has_content and i == 0:
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
                continue

            if is_cursor_line and cursor_ch:
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

        lines.append(Text.assemble(
            (f"  {H_BOT_L}", "dim"),
            (f"{H_LINE * content_width}", "dim"),
            (f"{H_BOT_R}", "dim"),
        ))

        scroll_info = ""
        if total_lines > max_display_lines:
            scroll_info = f"{start_line + 1}-{min(start_line + max_display_lines, total_lines)}/{total_lines}"

        # Conversation context indicator
        turn_hint = f" Turn #{turn_count}" if turn_count > 0 else ""
        
        # Animated status indicator
        typing_dots = _THINKING_DOTS[self._thinking_dot_frame] if self._is_typing else ""
        mode_color = _MODE_SCHEMES.get(self.mode, "white")
        
        mode_tag = Text.assemble((f"[{self.get_mode_display()}]", f"bold {mode_color}"))
        status_icon = "●" if self._is_typing else "○"
        status = Text.assemble(
            (f"{status_icon} ", "green" if self._is_typing else "dim"),
            (f"typing{typing_dots}" if self._is_typing else "ready", "green" if self._is_typing else "dim"),
        )
        
        left_info = f" [{self.get_mode_display()}]  {status_icon} {'typing' if self._is_typing else 'ready'}"
        if scroll_info:
            left_info += f"  {scroll_info}"
        # Turn count is rendered as turn_hint, NOT counted in left_info for padding
        right_info = f"{self.current_model}  Enter · Shift+Enter"
        pad = max(4, box_width - 2 - len(left_info) - len(right_info))

        info_line = Text.assemble(
            ("   ", ""), mode_tag, ("  ", ""), status,
            (" " * pad, ""),
            (scroll_info + "  " if scroll_info else "", "dim"),
            (f"{turn_hint}", "bold green"),
            (f"{self.current_model}", "bold yellow"),
            ("  Enter", "dim"), (" · ", "dim"), ("Shift+Enter", "dim"),
        )

        return Group(*lines, info_line)
