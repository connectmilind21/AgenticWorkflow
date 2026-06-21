"""
Short-term memory implementation - sliding window conversation history.
"""

from __future__ import annotations

from collections import deque
from typing import Any

from memory.base import BaseMemory, MemoryEntry


class ShortTermMemory(BaseMemory):
    """
    In-memory sliding window for recent conversation/interaction history.

    Keeps the last N messages (configurable window size) in a deque for
    fast access. Does not persist across process restarts.
    """

    def __init__(
        self,
        max_messages: int = 50,
        window_size: int = 10,
    ) -> None:
        self.max_messages = max_messages
        self.window_size = window_size
        self._store: deque[MemoryEntry] = deque(maxlen=max_messages)

    def add(self, content: Any, **kwargs: Any) -> MemoryEntry:
        """Add a new entry to short-term memory."""
        entry = MemoryEntry(
            content=content,
            role=kwargs.get("role", "user"),
            metadata=kwargs.get("metadata", {}),
            tags=kwargs.get("tags", []),
        )
        self._store.append(entry)
        return entry

    def get(self, entry_id: str) -> MemoryEntry | None:
        """Retrieve a specific entry by ID."""
        for entry in self._store:
            if entry.id == entry_id:
                return entry
        return None

    def search(self, query: str, limit: int = 10) -> list[MemoryEntry]:
        """Search memory entries containing the query string."""
        query_lower = query.lower()
        results: list[MemoryEntry] = []

        for entry in reversed(self._store):
            content_str = str(entry.content).lower()
            if query_lower in content_str:
                results.append(entry)
            if len(results) >= limit:
                break

        return results

    def get_window(self) -> list[MemoryEntry]:
        """Return the most recent entries within the window size."""
        entries = list(self._store)
        return entries[-self.window_size :] if entries else []

    def get_conversation_history(self) -> list[dict[str, Any]]:
        """Return conversation history in LLM-compatible format."""
        return [
            {"role": entry.role, "content": str(entry.content)}
            for entry in self.get_window()
        ]

    def clear(self) -> None:
        """Clear all short-term memory."""
        self._store.clear()

    def get_all(self) -> list[MemoryEntry]:
        """Return all entries."""
        return list(self._store)
