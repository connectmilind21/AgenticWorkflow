"""
Long-term memory implementation - persistent storage for agent knowledge.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import structlog

from memory.base import BaseMemory, MemoryEntry

logger = structlog.get_logger(__name__)


class LongTermMemory(BaseMemory):
    """
    Persistent long-term memory with JSON file backend (default) or database.

    Stores memories in a structured format with full-text search capability.
    For production use, configure a PostgreSQL backend via the database_url.
    """

    def __init__(
        self,
        storage_path: str | None = None,
        database_url: str | None = None,
        namespace: str = "default",
    ) -> None:
        self.namespace = namespace
        self.database_url = database_url
        self._storage_path: Path | None = None
        self._in_memory: dict[str, MemoryEntry] = {}
        self._logger = logger.bind(namespace=namespace)

        if storage_path:
            self._storage_path = Path(storage_path)
            self._storage_path.parent.mkdir(parents=True, exist_ok=True)
            self._load_from_file()

    def add(self, content: Any, **kwargs: Any) -> MemoryEntry:
        """Add a new entry to long-term memory."""
        entry = MemoryEntry(
            content=content,
            role=kwargs.get("role", "user"),
            metadata=kwargs.get("metadata", {}),
            tags=kwargs.get("tags", []),
        )
        self._in_memory[entry.id] = entry

        if self._storage_path:
            self._persist()

        self._logger.debug("Memory added", entry_id=entry.id)
        return entry

    def get(self, entry_id: str) -> MemoryEntry | None:
        """Retrieve a specific entry by ID."""
        return self._in_memory.get(entry_id)

    def search(self, query: str, limit: int = 10) -> list[MemoryEntry]:
        """Full-text search across all memory entries."""
        query_lower = query.lower()
        scored: list[tuple[float, MemoryEntry]] = []

        for entry in self._in_memory.values():
            content_str = str(entry.content).lower()
            if query_lower in content_str:
                occurrences = content_str.count(query_lower)
                recency_score = 1.0 / (1.0 + (time.time() - entry.timestamp) / 3600)
                score = occurrences * 0.7 + recency_score * 0.3
                scored.append((score, entry))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [entry for _, entry in scored[:limit]]

    def get_by_tags(self, tags: list[str]) -> list[MemoryEntry]:
        """Retrieve entries matching any of the given tags."""
        tag_set = set(tags)
        return [
            entry
            for entry in self._in_memory.values()
            if tag_set.intersection(entry.tags)
        ]

    def get_recent(self, n: int = 10) -> list[MemoryEntry]:
        """Get the N most recently added entries."""
        sorted_entries = sorted(
            self._in_memory.values(),
            key=lambda e: e.timestamp,
            reverse=True,
        )
        return sorted_entries[:n]

    def clear(self) -> None:
        """Clear all long-term memory."""
        self._in_memory.clear()
        if self._storage_path and self._storage_path.exists():
            self._storage_path.write_text("{}")

    def get_all(self) -> list[MemoryEntry]:
        """Return all entries sorted by timestamp."""
        return sorted(self._in_memory.values(), key=lambda e: e.timestamp)

    def _persist(self) -> None:
        """Persist entries to JSON file."""
        if not self._storage_path:
            return
        data = {
            entry_id: entry.model_dump()
            for entry_id, entry in self._in_memory.items()
        }
        self._storage_path.write_text(json.dumps(data, indent=2, default=str))

    def _load_from_file(self) -> None:
        """Load entries from JSON file."""
        if not self._storage_path or not self._storage_path.exists():
            return
        try:
            data = json.loads(self._storage_path.read_text())
            for entry_id, entry_data in data.items():
                self._in_memory[entry_id] = MemoryEntry(**entry_data)
            self._logger.info(
                "Loaded memory from file",
                path=str(self._storage_path),
                count=len(self._in_memory),
            )
        except Exception as exc:
            self._logger.warning("Failed to load memory file", error=str(exc))
