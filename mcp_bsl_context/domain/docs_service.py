"""Service for BSL documentation: strict typing guide and coding guidelines."""

from __future__ import annotations

import re
from pathlib import Path

from mcp_bsl_context.domain.exceptions import (
    DomainException,
    InvalidSearchQueryException,
)

TOPIC_PATTERN = re.compile(r"^## TOPIC:\s*(.+)$", re.MULTILINE)

CONTEXT_CHARS = 100


class TopicNotFoundException(DomainException):
    pass


class DocsLoadException(DomainException):
    pass


class DocsInfoService:
    """Loads and queries bundled BSL documentation files."""

    def __init__(
        self,
        strict_types_content: str,
        guideline_content: str,
    ) -> None:
        self._strict_types_content = strict_types_content
        self._guideline_content = guideline_content
        self._topics: dict[str, str] | None = None

    def get_guideline(self) -> str:
        """Return full guideline markdown content."""
        return self._guideline_content

    def get_strict_typing_info(self, topic: str) -> str:
        """Return a specific topic section, or list all topic names."""
        topics = self._ensure_topics()

        if topic.strip().lower() == "topics":
            lines = ["**Доступные темы по строгой типизации:**\n"]
            for name in topics:
                lines.append(f"- `{name}`")
            return "\n".join(lines)

        key = topic.strip().lower()
        if key not in topics:
            available = ", ".join(f"`{n}`" for n in topics)
            raise TopicNotFoundException(
                f"Тема '{topic}' не найдена. Доступные темы: {available}"
            )

        return topics[key]

    def search_strict_typing(self, query: str) -> str:
        """Keyword search within strict-types content with context previews."""
        stripped = query.strip()
        if not stripped:
            raise InvalidSearchQueryException(
                "Поисковый запрос не может быть пустым"
            )

        topics = self._ensure_topics()
        query_lower = stripped.lower()
        results: list[str] = []

        for name, content in topics.items():
            content_lower = content.lower()
            pos = content_lower.find(query_lower)
            if pos == -1:
                continue

            start = max(0, pos - CONTEXT_CHARS)
            end = min(len(content), pos + len(stripped) + CONTEXT_CHARS)
            preview = content[start:end].strip()
            if start > 0:
                preview = "..." + preview
            if end < len(content):
                preview = preview + "..."

            results.append(f"### Тема: `{name}`\n\n{preview}")

        if not results:
            return f"По запросу «{stripped}» ничего не найдено."

        header = f"**Результаты поиска по запросу «{stripped}»** ({len(results)} совпадений):\n"
        return header + "\n\n---\n\n".join(results)

    def _ensure_topics(self) -> dict[str, str]:
        if self._topics is None:
            self._topics = self._parse_topics(self._strict_types_content)
        return self._topics

    @staticmethod
    def _parse_topics(content: str) -> dict[str, str]:
        """Parse strict-types markdown into topic sections."""
        parts = TOPIC_PATTERN.split(content)
        topics: dict[str, str] = {}

        # parts[0] is text before first TOPIC header (preamble, skip)
        # then alternating: topic_name, topic_content, topic_name, ...
        i = 1
        while i < len(parts) - 1:
            name = parts[i].strip().lower()
            body = parts[i + 1].strip()
            topics[name] = body
            i += 2

        return topics
