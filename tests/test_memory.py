"""
Tests for memory implementations.
"""

from __future__ import annotations

import time

import pytest

from memory.base import MemoryEntry
from memory.long_term import LongTermMemory
from memory.short_term import ShortTermMemory
from memory.vector_store import VectorStoreMemory


class TestMemoryEntry:
    """Tests for MemoryEntry model."""

    def test_creation_with_defaults(self):
        """Creates entry with auto-generated id and timestamp."""
        entry = MemoryEntry(content="hello")
        assert entry.id is not None
        assert entry.content == "hello"
        assert entry.role == "user"
        assert entry.timestamp > 0
        assert entry.metadata == {}
        assert entry.tags == []

    def test_creation_with_custom_fields(self):
        """Allows custom fields."""
        entry = MemoryEntry(
            content={"key": "value"},
            role="assistant",
            tags=["important"],
            metadata={"source": "test"},
        )
        assert entry.role == "assistant"
        assert "important" in entry.tags
        assert entry.metadata["source"] == "test"


class TestShortTermMemory:
    """Tests for ShortTermMemory."""

    @pytest.fixture
    def memory(self):
        return ShortTermMemory(max_messages=10, window_size=5)

    def test_initialization(self, memory):
        assert memory.max_messages == 10
        assert memory.window_size == 5
        assert len(memory) == 0

    def test_add_entry(self, memory):
        """Adds entry and returns MemoryEntry."""
        entry = memory.add("test content")
        assert isinstance(entry, MemoryEntry)
        assert entry.content == "test content"
        assert len(memory) == 1

    def test_add_with_role(self, memory):
        """Stores role correctly."""
        entry = memory.add("assistant reply", role="assistant")
        assert entry.role == "assistant"

    def test_max_messages_enforced(self):
        """Drops oldest entries when max is reached."""
        memory = ShortTermMemory(max_messages=3)
        for i in range(5):
            memory.add(f"message {i}")
        assert len(memory) == 3

    def test_get_by_id(self, memory):
        """Retrieves entry by ID."""
        entry = memory.add("find me")
        found = memory.get(entry.id)
        assert found is not None
        assert found.content == "find me"

    def test_get_missing_id_returns_none(self, memory):
        """Returns None for unknown IDs."""
        assert memory.get("nonexistent-id") is None

    def test_search_finds_matching(self, memory):
        """Searches content by substring."""
        memory.add("Python is great")
        memory.add("Java is verbose")
        results = memory.search("Python")
        assert len(results) == 1
        assert "Python" in str(results[0].content)

    def test_search_case_insensitive(self, memory):
        """Search is case-insensitive."""
        memory.add("Machine Learning concepts")
        results = memory.search("machine learning")
        assert len(results) == 1

    def test_get_window_returns_recent(self, memory):
        """Returns only window_size most recent entries."""
        for i in range(7):
            memory.add(f"msg {i}")
        window = memory.get_window()
        assert len(window) == 5

    def test_get_conversation_history(self, memory):
        """Returns LLM-compatible format."""
        memory.add("Hello", role="user")
        memory.add("Hi there", role="assistant")
        history = memory.get_conversation_history()
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"

    def test_clear(self, memory):
        """Clears all entries."""
        memory.add("entry 1")
        memory.add("entry 2")
        memory.clear()
        assert len(memory) == 0

    def test_get_all(self, memory):
        """Returns all entries."""
        memory.add("a")
        memory.add("b")
        all_entries = memory.get_all()
        assert len(all_entries) == 2


class TestLongTermMemory:
    """Tests for LongTermMemory."""

    @pytest.fixture
    def memory(self):
        return LongTermMemory(namespace="test")

    @pytest.fixture
    def persistent_memory(self, tmp_path):
        storage = str(tmp_path / "memory.json")
        return LongTermMemory(storage_path=storage, namespace="test_persist")

    def test_initialization(self, memory):
        assert memory.namespace == "test"
        assert len(memory) == 0

    def test_add_and_retrieve(self, memory):
        """Adds and retrieves an entry."""
        entry = memory.add("important fact", role="user", tags=["fact"])
        found = memory.get(entry.id)
        assert found is not None
        assert found.content == "important fact"

    def test_search_by_content(self, memory):
        """Full-text search works."""
        memory.add("The capital of France is Paris")
        memory.add("Tokyo is in Japan")
        results = memory.search("France")
        assert len(results) == 1

    def test_search_returns_most_relevant_first(self, memory):
        """Returns most relevant results first."""
        memory.add("Python Python Python")
        memory.add("Python once")
        results = memory.search("Python", limit=2)
        assert "Python Python Python" in str(results[0].content)

    def test_get_by_tags(self, memory):
        """Retrieves entries by tags."""
        memory.add("financial data", tags=["finance"])
        memory.add("medical data", tags=["health"])
        memory.add("tech news", tags=["tech", "news"])
        results = memory.get_by_tags(["finance"])
        assert len(results) == 1

    def test_get_recent(self, memory):
        """Returns N most recently added entries."""
        for i in range(5):
            memory.add(f"entry {i}")
            time.sleep(0.001)
        recent = memory.get_recent(3)
        assert len(recent) == 3

    def test_clear(self, memory):
        """Clears all entries."""
        memory.add("to be deleted")
        memory.clear()
        assert len(memory) == 0

    def test_persistence(self, tmp_path):
        """Persists and loads from file."""
        storage = str(tmp_path / "memory.json")
        m1 = LongTermMemory(storage_path=storage)
        m1.add("persist this", role="user")

        m2 = LongTermMemory(storage_path=storage)
        assert len(m2) == 1
        results = m2.search("persist")
        assert len(results) == 1


class TestVectorStoreMemory:
    """Tests for VectorStoreMemory."""

    @pytest.fixture
    def memory(self):
        return VectorStoreMemory(backend="memory")

    def test_initialization(self, memory):
        assert memory.backend == "memory"
        assert len(memory) == 0

    def test_add_entry(self, memory):
        """Adds entry successfully."""
        entry = memory.add("vector memory test")
        assert isinstance(entry, MemoryEntry)
        assert len(memory) == 1

    def test_search_keyword(self, memory):
        """Keyword-based fallback search works."""
        memory.add("deep learning neural networks")
        memory.add("database SQL queries")
        results = memory.search("neural networks")
        assert len(results) >= 1
        assert any("neural" in str(r.content) for r in results)

    def test_get_by_id(self, memory):
        """Retrieves entry by ID."""
        entry = memory.add("find this")
        found = memory.get(entry.id)
        assert found is not None

    def test_get_missing_returns_none(self, memory):
        """Returns None for unknown ID."""
        assert memory.get("nonexistent") is None

    def test_clear(self, memory):
        """Clears all entries."""
        memory.add("entry 1")
        memory.add("entry 2")
        memory.clear()
        assert len(memory) == 0

    def test_get_all(self, memory):
        """Returns all entries."""
        memory.add("a")
        memory.add("b")
        all_entries = memory.get_all()
        assert len(all_entries) == 2
