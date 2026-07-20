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
from rich.table import Table
from rich.text import Text

from ..client.api import MyAgentAPI
from .commands import CommandHandler, CommandResult
from .input import InputHandler, KeyReader
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
        self._system_prompt_added = False
        self._live: Optional[Live] = None
        self._layout: Optional[Layout] = None
        self._last_git_check = 0.0
        self._terminal_width = 120
        self._has_repo = False
        self._ollama_checked = False
        self._cancelled = False

        # Streaming throttle (60fps ≈ 16ms, but polling is at 50ms to save CPU)
        self._last_stream_refresh = 0.0
        
        # Conversation context count (for display)
        self._turn_count = 0
        


        # Layout sections (created in _build_layout)
        self._layout_header: Optional[Layout] = None
        self._layout_main: Optional[Layout] = None
        self._layout_input: Optional[Layout] = None
        self._layout_status: Optional[Layout] = None

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

    def _get_terminal_height(self) -> int:
        try:
            return os.get_terminal_size().lines
        except Exception:
            return 24

    def _build_layout(self) -> Layout:
        """Build the multi-panel layout.
        
        Layout structure (top to bottom):
          header  (1 line)   - fixed, always visible
          main    (ratio=1)  - conversation area (agent + optional sidebars)
          input   (4/2 line) - fixed, ALWAYS visible composer
          status  (1 line)   - fixed, always visible
          
        CRITICAL: Does NOT use nested split_row for main area.
        Instead, the main Layout is updated directly with the agent panel
        (or a Columns of panels) in _render_panels.
        This avoids a known issue where nested Layout children fail to render.
        """
        # Read terminal dimensions
        width = self._get_terminal_width()
        height = self._get_terminal_height()
        self._terminal_width = width
        self.agent._terminal_width = width

        # Input size based on terminal height
        input_size = 2 if height < 15 else 4

        # Create root layout sections
        self._layout_header = Layout(name="header", size=1)
        self._layout_main = Layout(name="main", ratio=1)
        self._layout_input = Layout(name="input", size=input_size)
        self._layout_status = Layout(name="status", size=1)

        # Build root layout - NO nested split_row!
        layout = Layout()
        layout.split_column(
            self._layout_header,
            self._layout_main,
            self._layout_input,
            self._layout_status,
        )

        # Determine sidebar visibility (hiding BEFORE input/status)
        if width < 80:
            self.explorer.visible = False
            self.context.visible = False
        elif width < 110:
            self.explorer.visible = False
            self.context.visible = True
        else:
            self.explorer.visible = True
            self.context.visible = True

        # The main layout is updated directly in _render_panels
        # No split_row needed!

        return layout

    def _build_main_renderable(self):
        """Build the main area renderable with proper proportional sizing.
        
        Uses Table with explicit ratios instead of nested Layout or Columns
        for reliable side-by-side display.
        
        Returns: agent panel directly, or a Table containing agent + sidebars.
        """
        try:
            # Build table columns based on visible panels
            columns = []
            row = []

            if self.explorer.visible:
                columns.append({"ratio": 2, "renderable": self.explorer})

            columns.append({"ratio": 5, "renderable": self.agent})

            if self.context.visible:
                columns.append({"ratio": 2, "renderable": self.context})

            if len(columns) > 1:
                table = Table(
                    show_header=False, show_edge=False,
                    show_lines=False, padding=0, expand=True,
                )
                for col in columns:
                    table.add_column(ratio=col["ratio"])
                table.add_row(*[c["renderable"] for c in columns])
                return table
            else:
                return self.agent
        except Exception:
            return self.agent

    def _render_panels(self):
        """Render all panels into the layout using direct Layout updates.
        
        The agent panel (+ optional sidebars) is rendered directly into
        layout_main using Table for proportional sizing.
        Input and status areas are ALWAYS rendered.
        """
        # ── Header ──
        if self._layout_header is not None:
            try:
                self._layout_header.update(self.header)
            except Exception:
                pass

        # ── Main area: agent + optional sidebars ──
        if self._layout_main is not None:
            try:
                self._layout_main.update(self._build_main_renderable())
            except Exception as e:
                try:
                    self._layout_main.update(Text(f"Main area: {e}"))
                except Exception:
                    pass

        # ── Input area - ALWAYS visible ──                if self._layout_input is not None:
                    try:
                        self._layout_input.update(self.agent.render_composer(self._turn_count))
                    except Exception:
                        try:
                            self._layout_input.update(Text("Input area"))
                        except Exception:
                            pass

        # ── Status bar - ALWAYS visible ──
        if self._layout_status is not None:
            try:
                self._layout_status.update(self.status)
            except Exception:
                try:
                    self._layout_status.update(Text("Status bar"))
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
        # Pass terminal dimensions for dynamic composer sizing
        self.agent._terminal_width = self._get_terminal_width()
        self.agent._terminal_height = self._get_terminal_height()
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
                try:
                    self._live.update(self._layout)
                except Exception:
                    pass

            self._sync_state()
            self._render_panels()
            try:
                self._live.refresh()
            except Exception:
                pass

    def _refresh_streaming(self):
        """Fast refresh during streaming.
        
        Updates agent (spinner + streaming content), input area, and status bar.
        Uses _build_main_renderable() to rebuild the main area including sidebars.
        """
        if self._live:
            self.agent.agent_state = "thinking"
            self.agent.tick_spinner()  # Advance spinner animation
            self.status.agent_state = "thinking"
            self.status.context_pct = self.context.context_percent()
            try:
                if self._layout_main is not None:
                    self._layout_main.update(self._build_main_renderable())
                if self._layout_input is not None:
                    self._layout_input.update(self.agent.render_composer(self._turn_count))
                if self._layout_status is not None:
                    self._layout_status.update(self.status)
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

    def _ensure_system_prompt(self):
        """Inject system prompt at the start of conversation if not already added.
        
        This ensures the LLM maintains conversation context across turns.
        """
        if not self._system_prompt_added:
            system_msg = {
                "role": "system",
                "content": (
                    "You are MyAgent, a world-class AI software engineering assistant. "
                    "You help users build, debug, analyze, and improve their code.\n\n"
                    "CONTEXT MAINTENANCE: This is a CONTINUING CONVERSATION. "
                    "You MUST remember and reference ALL previous messages in this conversation. "
                    "Each new message builds on what was discussed before. "
                    "Do not restart or forget context between messages.\n\n"
                    "Guidelines:\n"
                    "- Provide complete, working solutions\n"
                    "- Explain your reasoning clearly\n"
                    "- Reference previous context when relevant\n"
                    "- Be concise but thorough\n"
                    "- Format code with proper markdown code blocks"
                )
            }
            self.messages.insert(0, system_msg)
            self._system_prompt_added = True

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
                # Clear BOTH backend messages AND UI messages
                self.messages = []
                self.agent.clear()
                self._system_prompt_added = False
                self._turn_count = 0
                self.context.commands_run = 0
                self.context.files_read = 0
                self.context.files_changed = 0
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
            # Clear input area
            self.agent.input_text = ""
        else:
            # Ensure system prompt is set for conversation context
            if not self.messages:
                self._ensure_system_prompt()

            # Track conversation turn
            self._turn_count += 1

            # Regular chat message - stream from backend
            self.messages.append({"role": "user", "content": text})
            self.agent.add_message("user", text)
            self.agent.agent_state = "thinking"
            self.agent.streaming_content = ""
            self.agent.input_text = ""

            # Update status with turn info
            self.status.message_count = self._turn_count
            self.status.session_start = getattr(self.status, 'session_start', time.time())

            self._refresh_display()

            # Create a plan for complex requests
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
            self._cancelled = False
            self._last_stream_refresh = 0.0

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
                        now = time.monotonic()
                        if now - self._last_stream_refresh >= 0.03:
                            self._last_stream_refresh = now
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
        """Main TUI loop with proper Live management and interactive input."""
        self.running = True
        self._interrupted = False

        # Initial health check
        await self._check_health()

        # Initial layout build
        self._layout = self._build_layout()

        # Initial git check
        self._update_git_state()
        self._sync_state()

        # Start the key reader
        self.key_reader = KeyReader()
        self.key_reader.start()

        console = Console()

        # Use Live for rendering
        with Live(
            self._layout,
            console=console,
            screen=False,
            refresh_per_second=12,
            vertical_overflow="visible",
        ) as live:
            self._live = live

            # Set session start
            now = time.time()
            self.context._session_start = now
            self.status.session_start = now

            while self.running:
                # Advance agent animations
                self.agent.tick_spinner()

                # Enter interactive reading mode
                self.agent._is_typing = False
                self.agent.input_text = ""
                self.agent.input_cursor_row = 0
                self.agent.input_cursor_col = 0
                self.input_handler.reset()
                self._refresh_display()

                # ── Interactive key-reading loop (60fps compatible, CPU-efficient) ──
                submitted_text: Optional[str] = None
                cursor_tick = 0

                while submitted_text is None and self.running:
                    try:
                        key = await asyncio.wait_for(
                            self.key_reader.next_key(),
                            timeout=0.05,  # 20fps polling - saves CPU
                        )
                    except asyncio.TimeoutError:
                        self.agent.tick_spinner()

                        # Cursor blink every ~1s (20 ticks at 50ms)
                        cursor_tick += 1
                        if cursor_tick >= 20:
                            self.agent._tick_cursor()
                            cursor_tick = 0

                        # Always refresh to show cursor blink + animations
                        self._refresh_display()
                        continue
                    except (Exception, asyncio.CancelledError):
                        submitted_text = "/exit"
                        break

                    # Process the key via InputHandler
                    result = self.input_handler.handle_key(key)
                    self.agent.input_text = self.input_handler.buffer.text
                    self.agent.input_cursor_row = self.input_handler.buffer.cursor_row
                    self.agent.input_cursor_col = self.input_handler.buffer.cursor_col
                    self.agent._is_typing = True

                    if result is not None:
                        submitted_text = result
                        break

                    self._refresh_display()

                # ── End of reading loop ──

                # Handle the submitted message
                user_input = submitted_text or ""

                if user_input == "__CANCEL__":
                    if self.agent.agent_state in ("thinking", "planning", "reading", "editing", "running", "testing"):
                        self._cancelled = True
                        self.agent.agent_state = "ready"
                        self.agent.streaming_content = ""
                        self._refresh_display()
                    continue

                if not user_input.strip():
                    continue

                if user_input == "/exit":
                    self.running = False
                    break

                # Process the message
                start_time = time.time()
                await self._handle_user_message(user_input.strip())
                self.agent.response_time = time.time() - start_time
                self.status.response_time = self.agent.response_time

                # Update session stats
                self.status.message_count = self.agent.session_message_count

                # Final refresh after processing
                self._refresh_display()

            # Stop the key reader
            await self.key_reader.stop()

            # Exit sequence
            self._live = None
            live.update(Text("Goodbye!", "bold cyan"))
            live.refresh()
            await asyncio.sleep(0.3)

        await self.api.close()
