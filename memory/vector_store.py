"""
Vector Store Memory - semantic search with embeddings.
"""

from __future__ import annotations

from typing import Any

import structlog

from memory.base import BaseMemory, MemoryEntry

logger = structlog.get_logger(__name__)


class VectorStoreMemory(BaseMemory):
    """
    Memory backend using vector embeddings for semantic similarity search.

    Supports:
    - ChromaDB (default, local)
    - Pinecone (cloud)
    - In-memory fallback with simple TF-IDF-like scoring
    """

    def __init__(
        self,
        backend: str = "memory",
        collection_name: str = "agent_memory",
        embedding_model: str | None = None,
        chroma_host: str = "localhost",
        chroma_port: int = 8000,
        pinecone_api_key: str | None = None,
        pinecone_index: str | None = None,
    ) -> None:
        self.backend = backend
        self.collection_name = collection_name
        self.embedding_model = embedding_model or "text-embedding-3-small"
        self.chroma_host = chroma_host
        self.chroma_port = chroma_port
        self.pinecone_api_key = pinecone_api_key
        self.pinecone_index = pinecone_index

        self._in_memory: dict[str, MemoryEntry] = {}
        self._client: Any | None = None
        self._collection: Any | None = None
        self._logger = logger.bind(backend=backend, collection=collection_name)

        if backend == "chroma":
            self._init_chroma()
        elif backend == "pinecone":
            self._init_pinecone()

    def _init_chroma(self) -> None:
        """Initialize ChromaDB client."""
        try:
            import chromadb

            self._client = chromadb.HttpClient(
                host=self.chroma_host, port=self.chroma_port
            )
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name
            )
            self._logger.info("ChromaDB initialized")
        except Exception as exc:
            self._logger.warning(
                "ChromaDB unavailable, using in-memory fallback",
                error=str(exc),
            )
            self._client = None
            self._collection = None

    def _init_pinecone(self) -> None:
        """Initialize Pinecone client."""
        try:
            from pinecone import Pinecone  # type: ignore[import-untyped]

            pc = Pinecone(api_key=self.pinecone_api_key)
            self._client = pc.Index(self.pinecone_index)
            self._logger.info("Pinecone initialized")
        except Exception as exc:
            self._logger.warning(
                "Pinecone unavailable, using in-memory fallback",
                error=str(exc),
            )
            self._client = None

    def add(self, content: Any, **kwargs: Any) -> MemoryEntry:
        """Add a new entry with embedding to the vector store."""
        entry = MemoryEntry(
            content=content,
            role=kwargs.get("role", "user"),
            metadata=kwargs.get("metadata", {}),
            tags=kwargs.get("tags", []),
        )
        self._in_memory[entry.id] = entry

        if self._collection is not None:
            self._add_to_chroma(entry)

        return entry

    def _add_to_chroma(self, entry: MemoryEntry) -> None:
        """Add entry to ChromaDB collection."""
        try:
            self._collection.add(
                documents=[str(entry.content)],
                ids=[entry.id],
                metadatas=[
                    {
                        "role": entry.role,
                        "timestamp": str(entry.timestamp),
                        **{k: str(v) for k, v in entry.metadata.items()},
                    }
                ],
            )
        except Exception as exc:
            self._logger.warning("Failed to add to ChromaDB", error=str(exc))

    def get(self, entry_id: str) -> MemoryEntry | None:
        """Retrieve a specific memory entry by ID."""
        return self._in_memory.get(entry_id)

    def search(self, query: str, limit: int = 10) -> list[MemoryEntry]:
        """Semantic search using vector similarity."""
        if self._collection is not None:
            return self._search_chroma(query, limit)
        return self._search_in_memory(query, limit)

    def _search_chroma(self, query: str, limit: int) -> list[MemoryEntry]:
        """Search using ChromaDB."""
        try:
            results = self._collection.query(
                query_texts=[query],
                n_results=min(limit, len(self._in_memory) or 1),
            )
            ids = results.get("ids", [[]])[0]
            return [
                self._in_memory[id_]
                for id_ in ids
                if id_ in self._in_memory
            ]
        except Exception as exc:
            self._logger.warning("ChromaDB search failed, using fallback", error=str(exc))
            return self._search_in_memory(query, limit)

    def _search_in_memory(self, query: str, limit: int) -> list[MemoryEntry]:
        """Simple keyword-based search for fallback."""
        query_terms = set(query.lower().split())
        scored: list[tuple[float, MemoryEntry]] = []

        for entry in self._in_memory.values():
            content_terms = set(str(entry.content).lower().split())
            overlap = query_terms.intersection(content_terms)
            if overlap:
                score = len(overlap) / len(query_terms)
                scored.append((score, entry))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in scored[:limit]]

    def clear(self) -> None:
        """Clear all stored memories."""
        self._in_memory.clear()
        if self._collection is not None:
            try:
                self._collection.delete(where={})
            except Exception:
                pass

    def get_all(self) -> list[MemoryEntry]:
        """Return all memory entries."""
        return list(self._in_memory.values())
