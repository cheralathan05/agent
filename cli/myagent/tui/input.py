"""Interactive input handler with cross-platform key reading, multiline editing,
cursor management, history, and slash-command autocomplete.

Reads individual keystrokes in a background thread so the Rich Live display
can be updated on every keypress. On Unix, uses termios.setraw() on stdin.
On Windows, uses msvcrt.getwch().
"""

import asyncio
import sys
from collections import deque
from dataclasses import dataclass
from typing import Callable, Optional


# ── Key event representation ──────────────────────

@dataclass
class Key:
    """A single keypress event."""
    type: str = "char"   # char, enter, shift_enter, backspace, delete,
                          # left, right, up, down, home, end, tab, shift_tab,
                          # esc, ctrl_c, ctrl_d, ctrl_l, ctrl_u, ctrl_w
    char: str = ""        # The actual character (for type='char')


# ── Slash command autocomplete ────────────────────

SLASH_COMMANDS = {
    "/help": "Show help menu",
    "/plan": "Create an implementation plan",
    "/build": "Switch to build mode",
    "/debug": "Switch to debug mode",
    "/review": "Switch to review mode",
    "/ask": "Switch to ask mode",
    "/mode": "Switch mode (plan/build/debug/review/ask)",
    "/model": "Switch model",
    "/models": "List available models",
    "/status": "Show system status",
    "/project": "Show project info",
    "/git": "Show git status",
    "/diff": "Show recent changes",
    "/approvals": "List pending approvals",
    "/allow": "Approve an action",
    "/deny": "Deny an action",
    "/checkpoint": "Save a checkpoint",
    "/undo": "Undo last operation",
    "/clear": "Clear the screen",
    "/history": "View command history",
    "/stop": "Cancel current operation",
    "/compact": "Compact conversation",
    "/exit": "Exit MyAgent",
}


def get_slash_completions(prefix: str) -> list[str]:
    """Get slash command completions for a given prefix."""
    if not prefix.startswith("/"):
        return []
    prefix = prefix.lower()
    return sorted(cmd for cmd in SLASH_COMMANDS if cmd.startswith(prefix))


# ── Cross-platform key reader (runs in thread) ────

_is_windows = sys.platform == "win32"

if not _is_windows:
    import termios
    import tty
    import select
    import os


def _read_key_blocking() -> Key:
    """Read a single keypress from stdin (blocking, intended for thread).

    Cross-platform: Unix uses termios raw mode; Windows uses msvcrt.
    """
    if _is_windows:
        return _read_key_windows()
    return _read_key_unix()


def _read_key_unix() -> Key:
    """Read one keypress on Unix using termios raw mode.
    
    Uses os.read(fd, 1) to bypass Python's TextIOWrapper buffering,
    which would otherwise swallow escape sequence bytes.
    """
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        # Use os.read to bypass TextIOWrapper buffering
        byte_data = os.read(fd, 1)
    except (OSError, EOFError):
        byte_data = b"\x03"
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)

    if not byte_data:
        return Key("ctrl_c")

    ch = byte_data.decode("utf-8", errors="replace")

    # Escape sequences (arrows, home, end, delete, etc.)
    if ch == "\x1b":
        rest = b""
        # Read following bytes with os.read + short timeout (non-blocking)
        try:
            import select
            fd = sys.stdin.fileno()
            # Restore cooked mode temporarily for select? No - we already restored
            # The escape sequence bytes are still in the fd buffer, read them
            # immediately with short timeout using os.read
            import time
            timeout = 0.04
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                r, _, _ = select.select([fd], [], [], max(0, deadline - time.monotonic()))
                if not r:
                    break
                b = os.read(fd, 1)
                if not b:
                    break
                rest += b
        except (OSError, ValueError):
            pass

        seq = rest.decode("utf-8", errors="replace")

        mapping = {
            "[A": Key("up"),
            "[B": Key("down"),
            "[C": Key("right"),
            "[D": Key("left"),
            "[H": Key("home"),
            "[F": Key("end"),
            "[3~": Key("delete"),
            "[Z": Key("shift_tab"),
            "OA": Key("up"),
            "OB": Key("down"),
            "OC": Key("right"),
            "OD": Key("left"),
        }
        if seq in mapping:
            return mapping[seq]
        return Key("esc")

    # Control characters
    if ch == "\r" or ch == "\n":
        return Key("enter")
    if ch == "\x7f" or ch == "\b":
        return Key("backspace")
    if ch == "\x03":
        return Key("ctrl_c")
    if ch == "\x04":
        return Key("ctrl_d")
    if ch == "\x0c":
        return Key("ctrl_l")
    if ch == "\x15":
        return Key("ctrl_u")
    if ch == "\x17":
        return Key("ctrl_w")
    if ch == "\t":
        return Key("tab")

    # Regular printable character
    return Key("char", ch)


def _read_key_windows() -> Key:
    """Read one keypress on Windows using msvcrt."""
    import msvcrt

    try:
        ch = msvcrt.getwch()
    except (EOFError, KeyboardInterrupt):
        return Key("ctrl_c")

    # Function keys (arrows, etc.) start with \xe0 or \x00
    if ch == "\xe0" or ch == "\x00":
        try:
            ch2 = msvcrt.getwch()
        except Exception:
            return Key("esc")
        mapping = {
            "H": Key("up"),
            "P": Key("down"),
            "M": Key("right"),
            "K": Key("left"),
            "G": Key("home"),
            "O": Key("end"),
            "s": Key("delete"),     # Ctrl+-
            "R": Key("delete"),     # Alt+-
        }
        return mapping.get(ch2, Key("esc"))

    # Control characters
    if ch == "\r":
        return Key("enter")
    if ch == "\b":
        return Key("backspace")
    if ch == "\x03":
        return Key("ctrl_c")
    if ch == "\x1b":
        return Key("esc")
    if ch == "\t":
        return Key("tab")

    # Regular character
    return Key("char", ch)


# ── Async key reader ──────────────────────────────

class KeyReader:
    """Reads individual keypresses asynchronously using a thread."""

    def __init__(self):
        self._queue: asyncio.Queue[Key] = asyncio.Queue()
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def start(self):
        """Start the background key-reading thread."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._reader_loop())

    async def stop(self):
        """Stop the key reader."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def next_key(self) -> Key:
        """Wait for and return the next keypress."""
        return await self._queue.get()

    async def _reader_loop(self):
        """Run the blocking key reader in a thread executor."""
        loop = asyncio.get_event_loop()
        while self._running:
            try:
                key = await loop.run_in_executor(None, _read_key_blocking)
                await self._queue.put(key)
            except Exception:
                await self._queue.put(Key("ctrl_c"))
                break


# ── Input line buffer with cursor, history, multiline ──

class InputBuffer:
    """Manages a multiline input buffer with cursor position and editing."""

    def __init__(self, max_lines: int = 20, max_cols: int = 72):
        self.lines: list[str] = [""]
        self.cursor_row: int = 0       # Which line (0-based)
        self.cursor_col: int = 0       # Column within the line (0-based)
        self.max_lines = max_lines
        self.max_cols = max_cols

    def reset(self):
        """Clear the buffer."""
        self.lines = [""]
        self.cursor_row = 0
        self.cursor_col = 0

    @property
    def text(self) -> str:
        """Get the full text as a single string."""
        return "\n".join(self.lines)

    @text.setter
    def text(self, value: str):
        """Set the full text from a string."""
        self.lines = value.split("\n") if value else [""]
        # Clamp
        if len(self.lines) > self.max_lines:
            self.lines = self.lines[:self.max_lines]
        # Ensure at least one line
        if not self.lines:
            self.lines = [""]
        # Move cursor to end
        self.cursor_row = len(self.lines) - 1
        self.cursor_col = len(self.lines[-1])

    # ── Editing actions ──

    def insert_char(self, ch: str):
        """Insert a character at the cursor position."""
        if not self.lines:
            self.lines = [""]
            self.cursor_row = 0
            self.cursor_col = 0
        line = self.lines[self.cursor_row]
        if self.cursor_col <= len(line):
            new_line = line[:self.cursor_col] + ch + line[self.cursor_col:]
            # Enforce max_cols per line
            if len(new_line) <= self.max_cols:
                self.lines[self.cursor_row] = new_line
                self.cursor_col += 1

    def newline(self):
        """Insert a newline at the cursor (split the current line)."""
        line = self.lines[self.cursor_row]
        before = line[:self.cursor_col]
        after = line[self.cursor_col:]
        self.lines[self.cursor_row] = before
        self.lines.insert(self.cursor_row + 1, after)
        # Clamp lines
        if len(self.lines) > self.max_lines:
            self.lines = self.lines[:self.max_lines]
            self.cursor_row = min(self.cursor_row, len(self.lines) - 1)
        else:
            self.cursor_row += 1
        self.cursor_col = 0

    def backspace(self):
        """Delete character before the cursor."""
        if not self.lines:
            return
        if self.cursor_col > 0:
            line = self.lines[self.cursor_row]
            self.lines[self.cursor_row] = line[:self.cursor_col - 1] + line[self.cursor_col:]
            self.cursor_col -= 1
        elif self.cursor_row > 0:
            # Join with previous line
            prev_line = self.lines[self.cursor_row - 1]
            curr_line = self.lines.pop(self.cursor_row)
            self.cursor_row -= 1
            self.cursor_col = len(prev_line)
            self.lines[self.cursor_row] = prev_line + curr_line

    def delete(self):
        """Delete character at the cursor."""
        if not self.lines:
            return
        line = self.lines[self.cursor_row]
        if self.cursor_col < len(line):
            self.lines[self.cursor_row] = line[:self.cursor_col] + line[self.cursor_col + 1:]
        elif self.cursor_row < len(self.lines) - 1:
            # Join with next line
            next_line = self.lines.pop(self.cursor_row + 1)
            self.lines[self.cursor_row] = line + next_line

    def cursor_left(self):
        """Move cursor left."""
        if self.cursor_col > 0:
            self.cursor_col -= 1
        elif self.cursor_row > 0:
            self.cursor_row -= 1
            self.cursor_col = len(self.lines[self.cursor_row])

    def cursor_right(self):
        """Move cursor right."""
        line = self.lines[self.cursor_row]
        if self.cursor_col < len(line):
            self.cursor_col += 1
        elif self.cursor_row < len(self.lines) - 1:
            self.cursor_row += 1
            self.cursor_col = 0

    def cursor_home(self):
        """Move cursor to start of current line."""
        self.cursor_col = 0

    def cursor_end(self):
        """Move cursor to end of current line."""
        self.cursor_col = len(self.lines[self.cursor_row])

    def cursor_up(self):
        """Move cursor up one line."""
        if self.cursor_row > 0:
            self.cursor_row -= 1
            self.cursor_col = min(self.cursor_col, len(self.lines[self.cursor_row]))

    def cursor_down(self):
        """Move cursor down one line."""
        if self.cursor_row < len(self.lines) - 1:
            self.cursor_row += 1
            self.cursor_col = min(self.cursor_col, len(self.lines[self.cursor_row]))

    def delete_to_start(self):
        """Delete from cursor to start of line (Ctrl+U)."""
        if not self.lines:
            return
        line = self.lines[self.cursor_row]
        self.lines[self.cursor_row] = line[self.cursor_col:]
        self.cursor_col = 0

    def delete_word_backward(self):
        """Delete word before cursor (Ctrl+W)."""
        if not self.lines or self.cursor_col == 0:
            return
        line = self.lines[self.cursor_row]
        # Find start of current word or previous word
        pos = self.cursor_col - 1
        while pos > 0 and line[pos] == " ":
            pos -= 1
        while pos > 0 and line[pos] != " ":
            pos -= 1
        if pos > 0 or (pos == 0 and line[0] != " "):
            # If we stopped at a space, move past it
            if line[pos] == " ":
                pos += 1
        self.lines[self.cursor_row] = line[:pos] + line[self.cursor_col:]
        self.cursor_col = pos


# ── Input handler (main interface) ────────────────

class InputHandler:
    """High-level input handler managing the buffer, history, and key dispatch.

    Tracks whether shift is held for distinguishing Enter from Shift+Enter.
    """

    def __init__(self, max_history: int = 100):
        self.buffer = InputBuffer()
        self.history: deque[str] = deque(maxlen=max_history)
        self._history_index = 0
        self._shift_pressed = False

    def add_to_history(self, text: str):
        text = text.strip()
        if text and (not self.history or self.history[-1] != text):
            self.history.append(text)
        self._history_index = len(self.history)

    def get_prev_history(self) -> Optional[str]:
        """Navigate to previous history item (up arrow on empty/at top)."""
        if not self.history:
            return None
        if self._history_index > 0:
            self._history_index -= 1
            return self.history[self._history_index]
        return None

    def get_next_history(self) -> Optional[str]:
        """Navigate to next history item (down arrow)."""
        if self._history_index < len(self.history) - 1:
            self._history_index += 1
            return self.history[self._history_index]
        elif self._history_index >= len(self.history) - 1:
            self._history_index = len(self.history)
            return ""
        return None

    def reset(self):
        """Reset the input buffer for a new message."""
        self.buffer.reset()

    @property
    def text(self) -> str:
        return self.buffer.text

    @text.setter
    def text(self, value: str):
        self.buffer.text = value

    def handle_key(self, key: Key) -> Optional[str]:
        """Process a key event. Returns the submitted text, or None if still editing.

        Returns:
          - A string (the submitted text) when Enter is pressed without Shift.
          - None when the buffer is still being edited.
        """
        if key.type == "char":
            self.buffer.insert_char(key.char)
        elif key.type == "enter":
            text = self.buffer.text.strip()
            if text:
                self.add_to_history(text)
            result = self.buffer.text
            self.reset()
            return result
        elif key.type == "shift_enter":
            self.buffer.newline()
        elif key.type == "backspace":
            self.buffer.backspace()
        elif key.type == "delete":
            self.buffer.delete()
        elif key.type == "left":
            self.buffer.cursor_left()
        elif key.type == "right":
            self.buffer.cursor_right()
        elif key.type == "up":
            if self.buffer.cursor_row > 0:
                self.buffer.cursor_up()
            else:
                # History navigation when on first line
                hist = self.get_prev_history()
                if hist is not None:
                    self.buffer.text = hist
        elif key.type == "down":
            if self.buffer.cursor_row < len(self.buffer.lines) - 1:
                self.buffer.cursor_down()
            else:
                # History navigation when on last line
                hist = self.get_next_history()
                if hist is not None:
                    self.buffer.text = hist
        elif key.type == "home":
            self.buffer.cursor_home()
        elif key.type == "end":
            self.buffer.cursor_end()
        elif key.type == "tab":
            # Autocomplete slash commands
            self._handle_tab_complete()
        elif key.type == "ctrl_c":
            return "__CANCEL__"
        elif key.type == "ctrl_u":
            self.buffer.delete_to_start()
        elif key.type == "ctrl_w":
            self.buffer.delete_word_backward()
        elif key.type == "esc":
            # Escape cancels current input
            self.reset()
            return "__CANCEL__"

        return None

    def _handle_tab_complete(self):
        """Attempt to autocomplete a slash command."""
        text = self.buffer.text
        completions = get_slash_completions(text)
        if len(completions) == 1:
            self.buffer.text = completions[0] + " "
            self.buffer.cursor_end()
        elif len(completions) > 1:
            # Find common prefix
            common = completions[0]
            for c in completions[1:]:
                while not c.startswith(common):
                    common = common[:-1]
            if common and common != text:
                self.buffer.text = common
                self.buffer.cursor_end()

    @staticmethod
    def is_slash_command(text: str) -> bool:
        return text.strip().startswith("/")

    @staticmethod
    def get_command_name(text: str) -> str:
        parts = text.strip().split()
        return parts[0].lower() if parts else ""
