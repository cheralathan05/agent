"""Secret detector - scans content for secrets before sending to LLM."""

from __future__ import annotations

import re
from typing import Any


class SecretDetector:
    """Detects secrets (API keys, tokens, passwords) in content."""

    # Patterns for common secrets
    SECRET_PATTERNS: list[tuple[str, str]] = [
        ("AWS Access Key", r"(?i)AKIA[0-9A-Z]{16}"),
        ("AWS Secret Key", r"(?i)(?<![A-Za-z0-9/+=])[A-Za-z0-9/+=]{40}(?![A-Za-z0-9/+=])"),
        ("GitHub Token", r"(?i)(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,}"),
        ("GitLab Token", r"(?i)glpat-[A-Za-z0-9\-_]{20,}"),
        ("Slack Token", r"(?i)xox[baprs]-[0-9A-Za-z\-]{10,}"),
        ("Discord Token", r"(?i)[A-Za-z0-9_]{24}\.[A-Za-z0-9_]{6}\.[A-Za-z0-9_\-]{27}"),
        ("JWT Token", r"(?i)eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+"),
        ("Password field", r"(?i)(\"password\"|\"passwd\"|\"pwd\")\s*:\s*\"[^\"]{3,}\""),
        ("API Key header", r"(?i)(x-api-key|api[_-]?key|api[_-]?secret)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}"),
        ("Private Key", r"-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"),
        ("Connection String", r"(?i)(postgresql|mysql|mongodb|redis)://[^:]+:[^@]+@"),
        ("Bearer Token", r"(?i)bearer\s+[A-Za-z0-9_\-\.]{20,}"),
        ("Slack Webhook", r"https://hooks\.slack\.com/services/[A-Za-z0-9]+/[A-Za-z0-9]+/[A-Za-z0-9]+"),
        ("Google Cloud Key", r"(?i)\"type\":\s*\"service_account\""),
    ]

    def __init__(self):
        self._compiled: list[tuple[str, re.Pattern]] = [
            (name, re.compile(pattern)) for name, pattern in self.SECRET_PATTERNS
        ]

    def detect(self, content: str) -> list[dict[str, Any]]:
        """Detect secrets in content. Returns list of findings."""
        findings = []
        for secret_name, pattern in self._compiled:
            matches = pattern.finditer(content)
            for match in matches:
                findings.append({
                    "type": secret_name,
                    "position": match.start(),
                    "length": match.end() - match.start(),
                    "preview": content[max(0, match.start() - 20): match.start()] + "[REDACTED]",
                })
        return findings

    def redact(self, content: str) -> str:
        """Redact all detected secrets from content."""
        redacted = content
        for secret_name, pattern in self._compiled:
            redacted = pattern.sub(f"[REDACTED_{secret_name.upper().replace(' ', '_')}]", redacted)
        return redacted

    def contains_secrets(self, content: str) -> bool:
        """Quick check if content contains any secrets."""
        for _, pattern in self._compiled:
            if pattern.search(content):
                return True
        return False


# Global secret detector
secret_detector = SecretDetector()
