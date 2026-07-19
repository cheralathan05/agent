"""Context builder for constructing LLM prompts with relevant context."""

from typing import Any


class ContextBuilder:
    """Builds context for LLM prompts with token budgeting."""

    def __init__(self, max_tokens: int = 8000):
        self.max_tokens = max_tokens
        self.sections: list[dict[str, Any]] = []

    def add_section(self, name: str, content: str, priority: int = 5):
        """Add a context section with priority (1=highest, 10=lowest)."""
        self.sections.append({
            "name": name,
            "content": content,
            "priority": priority,
        })

    def build(self) -> str:
        """Build the context string, prioritizing high-priority sections."""
        sorted_sections = sorted(self.sections, key=lambda s: s["priority"])

        context_parts = []
        for section in sorted_sections:
            context_parts.append(
                f"=== {section['name']} ===\n{section['content']}"
            )

        return "\n\n".join(context_parts)

    def clear(self):
        """Clear all sections."""
        self.sections = []
