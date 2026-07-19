"""Input handler with multiline composer, history, and slash command autocomplete."""

import asyncio
import sys
from collections import deque
from typing import Optional


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


class InputHandler:
    """Handles user input with multiline editing, history, and slash autocomplete.

    Uses a simple async input loop that reads from stdin.
    The prompt is rendered as part of the AgentPanel UI.
    """

    def __init__(self, max_history: int = 100):
        self.history: deque[str] = deque(maxlen=max_history)
        self._history_index = 0
        self._buffer: list[str] = []

    def add_to_history(self, text: str):
        text = text.strip()
        if text and (not self.history or self.history[-1] != text):
            self.history.append(text)
        self._history_index = len(self.history)

    def get_prev_history(self) -> Optional[str]:
        """Navigate to previous history item (up arrow)."""
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

    async def read(self) -> str:
        """Async read a line of input from stdin.

        Returns the text the user entered. The prompt rendering
        is handled by the AgentPanel composer area.
        
        This runs input() in a thread executor to avoid blocking.
        """
        loop = asyncio.get_event_loop()

        def _read():
            try:
                return input()
            except (EOFError, KeyboardInterrupt):
                return "/exit"

        user_input = await loop.run_in_executor(None, _read)
        self.add_to_history(user_input)
        return user_input

    @staticmethod
    def is_slash_command(text: str) -> bool:
        return text.strip().startswith("/")

    @staticmethod
    def get_command_name(text: str) -> str:
        parts = text.strip().split()
        return parts[0].lower() if parts else ""

    @staticmethod
    def get_completions(text: str) -> list[str]:
        """Get command completions. Returns empty list if no completions."""
        if text.startswith("/"):
            return get_slash_completions(text)
        return []
