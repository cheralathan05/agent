"""Command policy - validates and classifies terminal commands."""

from __future__ import annotations

import shlex
from typing import Any

from backend.app.config import settings


class CommandClassification:
    """Classification result for a command."""

    SAFE = "safe"
    CONFIRMATION = "confirmation"
    BLOCKED = "blocked"

    def __init__(self, classification: str, reason: str = ""):
        self.classification = classification
        self.reason = reason

    @property
    def is_safe(self) -> bool:
        return self.classification == self.SAFE

    @property
    def is_blocked(self) -> bool:
        return self.classification == self.BLOCKED

    @property
    def requires_confirmation(self) -> bool:
        return self.classification == self.CONFIRMATION


class CommandPolicy:
    """Validates and classifies terminal commands."""

    # Commands considered safe by default
    SAFE_COMMANDS = {
        "ls", "dir", "pwd", "cd", "echo", "cat", "type",
        "head", "tail", "wc", "sort", "uniq", "grep", "findstr",
        "find", "git status", "git diff", "git log", "git branch",
        "git stash list", "pip list", "pip freeze", "npm list",
        "cargo check", "go build", "python --version",
        "node --version", "npm --version", "python -m pytest --collect-only",
    }

    # Commands that require explicit confirmation
    CONFIRMATION_COMMANDS = {
        "git commit", "git push", "git merge", "git checkout",
        "git reset", "git stash", "git tag", "git rm", "git mv",
        "npm install", "npm uninstall", "pip install", "pip uninstall",
        "apt install", "brew install", "cargo install",
        "alembic upgrade", "alembic downgrade", "alembic revision",
        "docker build", "docker run", "docker compose",
        "mkdir", "rmdir", "del", "rm", "mv", "move", "cp", "copy",
        "chmod", "chown", ">", ">>", "|",
    }

    # Commands that should always be blocked
    BLOCKED_PATTERNS = [
        "rm -rf /", "rm -rf /*", "rm -rf ~",
        "mkfs", "format", "dd if=",
        ":(){ :|:& };:",  # Fork bomb
        "> /dev/sda", "> /dev/null",
        "chmod 777 /", "chmod -R 777 /",
        "sudo rm", "sudo dd", "sudo mkfs",
        "wget", "curl",
        "> /etc/", "> /boot/",
        "shutdown", "reboot", "poweroff", "halt",
    ]

    def classify(self, command: str) -> CommandClassification:
        """Classify a command as safe, confirmation-required, or blocked."""
        cmd_lower = command.strip().lower()

        # Check blocked patterns first
        for pattern in self.BLOCKED_PATTERNS:
            if pattern in cmd_lower:
                return CommandClassification(
                    CommandClassification.BLOCKED,
                    f"Command matches blocked pattern: {pattern}",
                )

        # Extract first two tokens for word-boundary matching
        tokens = cmd_lower.split()
        first_two = " ".join(tokens[:2]) if len(tokens) >= 2 else tokens[0] if tokens else ""
        first_one = tokens[0] if tokens else ""

        # Check if it's a known safe command
        for safe_cmd in self.SAFE_COMMANDS:
            safe_tokens = safe_cmd.split()
            if len(safe_tokens) == 1 and first_one == safe_cmd:
                return CommandClassification(CommandClassification.SAFE, "Known safe command")
            if len(safe_tokens) >= 2 and first_two == safe_cmd:
                return CommandClassification(CommandClassification.SAFE, "Known safe command")

        # Check if it requires confirmation
        for conf_cmd in self.CONFIRMATION_COMMANDS:
            conf_tokens = conf_cmd.split()
            if len(conf_tokens) == 1 and first_one == conf_cmd:
                return CommandClassification(
                    CommandClassification.CONFIRMATION,
                    f"Command requires confirmation: {first_one}",
                )
            if len(conf_tokens) >= 2 and first_two == conf_cmd:
                return CommandClassification(
                    CommandClassification.CONFIRMATION,
                    f"Command requires confirmation: {first_two}",
                )

        # Default to confirmation for unknown commands
        return CommandClassification(
            CommandClassification.CONFIRMATION,
            "Unknown command requires confirmation",
        )


# Global command policy
command_policy = CommandPolicy()
