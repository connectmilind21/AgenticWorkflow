"""
Base memory implementation for the Agentic Workflow Framework.
"""

from __future__ import annotations

import time
import uuid
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class MemoryEntry(BaseModel):
    """A single memory entry."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: Any
    role: str = "user"
    timestamp: float = Field(default_factory=time.time)
    metadata: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)


class BaseMemory(ABC):
    """
    Abstract base class for all memory backends.

    Memory stores are used by agents to persist and retrieve information
    across interactions and workflow steps.
    """

    @abstractmethod
    def add(self, content: Any, **kwargs: Any) -> MemoryEntry:
        """
        Add a new entry to memory.

        Args:
            content: Content to store (string, dict, etc.).
            **kwargs: Additional metadata (role, tags, etc.).

        Returns:
            The created MemoryEntry.
        """

    @abstractmethod
    def get(self, entry_id: str) -> MemoryEntry | None:
        """
        Retrieve a specific memory entry by ID.

        Args:
            entry_id: Unique identifier of the entry.

        Returns:
            MemoryEntry if found, None otherwise.
        """

    @abstractmethod
    def search(self, query: str, limit: int = 10) -> list[MemoryEntry]:
        """
        Search memory for relevant entries.

        Args:
            query: Search query.
            limit: Maximum number of results.

        Returns:
            List of relevant MemoryEntry objects.
        """

    @abstractmethod
    def clear(self) -> None:
        """Clear all memory entries."""

    @abstractmethod
    def get_all(self) -> list[MemoryEntry]:
        """Return all memory entries."""

    def __len__(self) -> int:
        return len(self.get_all())
