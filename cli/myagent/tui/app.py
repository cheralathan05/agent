"""Main MyAgent TUI application - orchestrates all panels and interaction."""

import asyncio
import os
import subprocess
import time
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.rule import Rule
from rich.text import Text

from ..client.api import MyAgentAPI
from .commands import CommandHandler, CommandResult
from .input import InputHandler
from .panels import HeaderPanel, ExplorerPanel, AgentPanel, ContextPanel, StatusBar


class MyAgentTUI:
    """Main TUI application managing layout, panels, and interaction loop.
    
    Uses Rich Layout for responsive panel management and Live for smooth updates.
    All panels are rendered without borders - clean text-based minimal design.
    """

    def __init__(
        self,
        api_base_url: str = "http://localhost:8000",
        workspace: Optional[Path] = None,
        model: Optional[str] = None,
    ):
        self.api = MyAgentAPI(api_base_url)
        self.workspace = Path(workspace or ".").resolve()

        # Panels
        self.header = HeaderPanel()
        self.explorer = ExplorerPanel(self.workspace)
        self.agent = AgentPanel()
        self.context = ContextPanel()
        self.status = StatusBar()

        # Input / Commands
        self.input_handler = InputHandler()
        self.command_handler = CommandHandler(self.api, self.workspace)

        # State
        self.running = False
        self.current_model = model or os.environ.get("OLLAMA_MODEL", "qwen3:8b")
        self.messages: list[dict] = []
        self._live: Optional[Live] = None
        self._layout: Optional[Layout] = None
        self._last_git_check = 0.0
        self._terminal_width = 120
        self._has_repo = False
        self._ollama_checked = False
        self._cancelled = False

        # Apply initial config
        self.header.model = self.current_model
        self.context.model = self.current_model
        self.status.model = self.current_model
        self.agent.current_model = self.current_model

    def _get_terminal_width(self) -> int:
        try:
            return os.get_terminal_size().columns
        except Exception:
            return 120

    def _build_layout(self) -> Layout:
        """Build the multi-panel layout with responsive visibility.
        
        Layout structure (top to bottom):
          header  (1 line)   - fixed, always visible
          main    (ratio=1)  - scrollable conversation area
          input   (4 lines)  - fixed, ALWAYS visible composer/input box
          status  (1 line)   - fixed, always visible
          
        The input area and status bar are ALWAYS visible regardless of
        content size or terminal dimensions. The right sidebar is hidden
        first when space is tight.
        """
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=1),
            Layout(name="main", ratio=1),
            Layout(name="input", size=4),
            Layout(name="status", size=1),
        )

        # Pass terminal width to agent panel for dynamic composer width
        width = self._get_terminal_width()
        self._terminal_width = width
        self.agent._terminal_width = width

        # Main area split - hide sidebar BEFORE clipping input or status
        if width < 80:
            # Small terminal: agent only - hide sidebar
            layout["main"].split_row(
                Layout(name="agent", ratio=1),
            )
            self.explorer.visible = False
            self.context.visible = False
        elif width < 110:
            # Medium terminal: agent + context (no explorer)
            layout["main"].split_row(
                Layout(name="agent", ratio=3),
                Layout(name="context", ratio=1),
            )
            self.explorer.visible = False
            self.context.visible = True
        else:
            # Large terminal: explorer + agent + context
            layout["main"].split_row(
                Layout(name="explorer", ratio=2),
                Layout(name="agent", ratio=5),
                Layout(name="context", ratio=1),
            )
            self.explorer.visible = True
            self.context.visible = True

        return layout

    def _render_panels(self, layout: Layout):
        """Render all panels into the layout.
        
        The input area and status bar are ALWAYS rendered.
        Side panels (explorer, context) are hidden on small terminals.
        """
        try:
            layout["header"].update(self.header)
        except Exception:
            layout["header"].update(Text(" ◆ MYAGENT", "bold cyan"))

        # ── Input area - ALWAYS visible ──
        try:
            layout["input"].update(self.agent.render_composer())
        except Exception:
            try:
                layout["input"].update(Text(" > "))
            except Exception:
                pass

        # ── Status bar - ALWAYS visible ──
        try:
            layout["status"].update(self.status)
        except Exception:
            layout["status"].update(Text(""))

        # ── Main area panels ──
        try:
            if self.explorer.visible:
                layout["explorer"].update(self.explorer)
            else:
                layout["explorer"].update(Text(""))
        except Exception:
            try:
                layout["explorer"].update(Text(""))
            except Exception:
                pass

        try:
            layout["agent"].update(self.agent)
        except Exception:
            try:
                layout["agent"].update(Text("Agent panel error"))
            except Exception:
                pass

        try:
            if self.context.visible:
                layout["context"].update(self.context)
            else:
                layout["context"].update(Text(""))
        except Exception:
            try:
                layout["context"].update(Text(""))
            except Exception:
                pass

    def _update_git_state(self):
        """Update git state with caching (max once per 3 seconds)."""
        now = time.time()
        if now - self._last_git_check < 3.0:
            return

        self._last_git_check = now
        try:
            # Check if git repo
            result = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                capture_output=True, text=True, timeout=2,
                cwd=self.workspace,
            )
            if result.returncode != 0 or result.stdout.strip() != "true":
                self._has_repo = False
                self.context._has_repo = False
                self.context.git_branch = None
                self.status.has_repo = False
                return

            self._has_repo = True
            self.context._has_repo = True
            self.status.has_repo = True

            # Get branch
            branch = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True, text=True, timeout=2, cwd=self.workspace,
            )
            if branch.returncode == 0 and branch.stdout.strip():
                self.context.git_branch = branch.stdout.strip()
                self.status.git_branch = branch.stdout.strip()

            # Get changes
            status_result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True, text=True, timeout=2, cwd=self.workspace,
            )
            if status_result.returncode == 0:
                changes = status_result.stdout.strip()
                if changes:
                    lines = [l for l in changes.split("\n") if l.strip()]
                    self.context.git_changes = len(lines)
                    self.status.git_changes = len(lines)
                    self.context.git_additions = sum(1 for l in lines if l.strip().startswith("A") or l.strip().startswith("??"))
                    self.context.git_deletions = sum(1 for l in lines if l.strip().startswith("D"))
                    self.status.git_additions = self.context.git_additions
                    self.status.git_deletions = self.context.git_deletions
                else:
                    self.context.git_changes = 0
                    self.status.git_changes = 0
                    self.context.git_additions = 0
                    self.context.git_deletions = 0
                    self.status.git_additions = 0
                    self.status.git_deletions = 0
        except Exception:
            pass

    def _sync_state(self):
        """Synchronize state across all panels."""
        self.context.model = self.current_model
        self.context.mode = self.agent.mode
        self.status.model = self.current_model
        self.status.mode = self.agent.mode
        self.status.agent_state = self.agent.agent_state
        self.status.context_pct = self.context.context_percent()
        # Pass terminal width for dynamic composer sizing
        self.agent._terminal_width = self._get_terminal_width()
        self._update_git_state()

    def _refresh_display(self):
        """Full refresh of the Live display.
        
        Always re-renders ALL panels including the fixed input area.
        Checks for terminal resize and adjusts layout accordingly.
        """
        if self._live:
            # Check if terminal was resized
            new_width = self._get_terminal_width()
            if abs(new_width - self._terminal_width) > 5:
                self._layout = self._build_layout()

            self._sync_state()
            self._render_panels(self._layout)
            try:
                self._live.refresh()
            except Exception:
                pass

    def _refresh_streaming(self):
        """Lightweight refresh during streaming.
        
        Updates agent panel (conversation + spinner) and status bar.
        The input area is ALWAYS refreshed to keep it visible.
        """
        if self._live:
            self.agent.agent_state = "thinking"
            self.agent.tick_spinner()  # Advance spinner animation
            self.status.agent_state = "thinking"
            self.status.context_pct = self.context.context_percent()
            try:
                self._layout["agent"].update(self.agent)
                self._layout["input"].update(self.agent.render_composer())
                self._layout["status"].update(self.status)
                self._live.refresh()
            except Exception:
                pass

    async def _check_health(self):
        """Check backend health and update status."""
        health = await self.api.health()
        status = health.get("status", "unavailable")

        self.header.ollama_status = status
        self.context.ollama_status = status
        self.status.ollama_status = status

        if status == "ok":
            llm = health.get("llm", {})
            llm_status = llm.get("status", "unknown")
            self.header.ollama_status = llm_status
            self.context.ollama_status = llm_status
            self.status.ollama_status = llm_status

            config_model = health.get("config", {}).get("model")
            if config_model:
                self.current_model = config_model
                self.header.model = config_model
                self.context.model = config_model
                self.status.model = config_model
                self.agent.current_model = config_model

        self._ollama_checked = True

    def _update_context_stats(self):
        """Update context usage stats based on actual messages."""
        token_estimate = sum(len(m.get("content", "")) // 4 for m in self.messages)
        self.context.context_used = min(self.context.context_limit, max(0, token_estimate))
        # Count unique files mentioned
        if self.messages:
            self.context.files_read = max(self.context.files_read, len(self.messages) // 2)

    async def _handle_user_message(self, text: str):
        """Process a user message - either a command or a chat message."""
        if InputHandler.is_slash_command(text):
            parts = text.strip().split()
            cmd_name = parts[0].lower() if parts else ""
            args = parts[1:]
            result = await self.command_handler.execute(cmd_name, args)

            if result.should_exit:
                self.running = False
                return

            if result.output == "__CLEAR__":
                self.agent.clear()
                return

            if result.output:
                self.agent.add_activity("✓", result.output, "green")
                self.agent.streaming_content = ""

            if result.error:
                self.agent.add_activity("✗", result.error, "red")
                self.agent.streaming_content = ""

            if result.mode_change:
                self.agent.mode = result.mode_change
                self.agent.agent_state = "ready"

            if result.model_change:
                self.current_model = result.model_change
                self.agent.current_model = result.model_change
                self.header.model = result.model_change
                self.context.model = result.model_change
                self.status.model = result.model_change

            self.context.commands_run += 1
        else:
            # Regular chat message - stream from backend
            self.messages.append({"role": "user", "content": text})
            self.agent.add_message("user", text)
            self.agent.agent_state = "thinking"
            self.agent.streaming_content = ""

            self._refresh_display()

            # Create a plan for complex requests (build/create/implement/add/make/analyze)
            is_complex = any(kw in text.lower() for kw in [
                "build", "create", "implement", "add", "make",
                "analyze", "fix", "debug", "refactor", "update",
            ])
            if is_complex:
                self.agent.plans = []
                self.agent.add_plan("Understanding request", "running")
                self.agent.add_plan("Analyzing project", "pending")
                self.agent.add_plan("Implementing changes", "pending")
                self.agent.add_plan("Verifying", "pending")

            self.agent.add_activity("●", "Thinking...", "cyan")
            self._refresh_display()

            # Stream response
            full_response = ""
            stream_count = 0
            display_count = 0
            self._cancelled = False

            try:
                async for data in self.api.stream_chat(self.messages, self.current_model):
                    if self._cancelled:
                        self.agent.add_activity("○", "Cancelled by user", "yellow")
                        break
                    event = data.get("event")
                    if event == "token":
                        chunk = data.get("data", {}).get("content", "")
                        full_response += chunk
                        self.agent.streaming_content = full_response
                        stream_count += 1
                        # Batch updates: every 5 tokens or every 200 chars
                        if stream_count % 5 == 0 or len(full_response) - display_count > 200:
                            display_count = len(full_response)
                            self._refresh_streaming()
                    elif event == "complete":
                        content = data.get("data", {}).get("content", "")
                        if content:
                            full_response = content
                    elif event == "error":
                        err_msg = data.get("data", {}).get("content", "Error during streaming")
                        self.agent.add_activity("✗", err_msg, "red")
                        self._refresh_streaming()
                        break
            except Exception as e:
                self.agent.add_activity("✗", f"Stream error: {str(e)}", "red")

            if full_response and not self._cancelled:
                self.messages.append({"role": "assistant", "content": full_response})
                self.agent.add_message("assistant", full_response)

            # Clean up streaming state
            self.agent.streaming_content = ""
            self.agent.agent_state = "completed"
            self.context.commands_run += 1

            # Mark plan as completed
            for i in range(len(self.agent.plans)):
                self.agent.update_plan(i, "completed")

            self._update_context_stats()

            # Refresh file explorer after mutations
            if any(kw in text.lower() for kw in ["create", "add", "delete", "remove", "rename", "build", "implement"]):
                self.explorer.refresh()

            self._refresh_display()

    async def run(self):
        """Main TUI loop with proper Live management."""
        self.running = True

        self._interrupted = False

        # Initial health check
        await self._check_health()

        # Initial layout build
        self._layout = self._build_layout()

        # Initial git check
        self._update_git_state()
        self._sync_state()

        console = Console()

        # Use Live for rendering
        with Live(
            self._layout,
            console=console,
            screen=False,
            refresh_per_second=8,
            vertical_overflow="visible",
        ) as live:
            self._live = live

            while self.running:
                # Show latest state before reading input
                self._refresh_display()

                try:
                    # Read input using simple input() - handled in executor
                    user_input = await self.input_handler.read()
                except (EOFError, KeyboardInterrupt):
                    # Ctrl+C: cancel operation if streaming, exit if idle
                    if self.agent.agent_state in ("thinking", "planning", "reading", "editing", "running", "testing"):
                        self._cancelled = True
                        self.agent.agent_state = "ready"
                        self.agent.streaming_content = ""
                        self._refresh_display()
                        continue
                    else:
                        user_input = "/exit"

                if not user_input.strip():
                    continue

                # Process the message
                await self._handle_user_message(user_input.strip())

                # Final refresh after processing
                self._refresh_display()

            # Exit sequence
            self._live = None
            live.update(Text("Goodbye!", "bold cyan"))
            live.refresh()
            await asyncio.sleep(0.3)

        await self.api.close()
