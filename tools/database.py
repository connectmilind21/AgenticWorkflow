"""
Database Tool - provides SQL query capabilities for agents.
"""

from __future__ import annotations

from typing import Any

import structlog

from tools.base import BaseTool

logger = structlog.get_logger(__name__)


class DatabaseTool(BaseTool):
    """
    Tool for executing database queries.

    Supports PostgreSQL and SQLite. Uses SQLAlchemy for portability.
    Only allows SELECT statements by default for safety.
    """

    def __init__(
        self,
        connection_url: str | None = None,
        allow_writes: bool = False,
        max_rows: int = 1000,
        enabled: bool = True,
    ) -> None:
        super().__init__(
            name="database",
            description=(
                "Executes SQL queries against a configured database. "
                "Supports SELECT (and optionally INSERT/UPDATE/DELETE)."
            ),
            enabled=enabled,
        )
        self.connection_url = connection_url
        self.allow_writes = allow_writes
        self.max_rows = max_rows
        self._engine: Any | None = None

    def run(self, input_data: Any, **kwargs: Any) -> list[dict[str, Any]]:
        """
        Execute a SQL query.

        Args:
            input_data: SQL query string or dict with "query" and optional "params".
            **kwargs: Additional query parameters.

        Returns:
            List of result rows as dictionaries.
        """
        if isinstance(input_data, dict):
            query = input_data.get("query", "")
            params = input_data.get("params", {})
        else:
            query = str(input_data)
            params = kwargs.get("params", {})

        self._validate_query(query)
        self._logger.info("Executing query", query=query[:100])

        if not self.connection_url:
            return self._mock_result(query)

        return self._execute(query, params)

    def _validate_query(self, query: str) -> None:
        """Validate the query is safe to execute."""
        normalized = query.strip().upper()

        if not self.allow_writes:
            write_keywords = {"INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER", "TRUNCATE"}
            first_word = normalized.split()[0] if normalized.split() else ""
            if first_word in write_keywords:
                raise PermissionError(
                    f"Write operation '{first_word}' not allowed. "
                    "Set allow_writes=True to enable."
                )

        dangerous = ["--", ";--", "/*", "*/", "xp_", "exec("]
        if any(d in query.lower() for d in dangerous):
            raise ValueError("Potentially unsafe SQL detected.")

    def _execute(
        self, query: str, params: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Execute the query using SQLAlchemy."""
        try:
            from sqlalchemy import create_engine, text

            if self._engine is None:
                self._engine = create_engine(self.connection_url)

            with self._engine.connect() as conn:
                result = conn.execute(text(query), params)
                if result.returns_rows:
                    rows = result.fetchmany(self.max_rows)
                    keys = list(result.keys())
                    return [dict(zip(keys, row)) for row in rows]
                return [{"affected_rows": result.rowcount}]
        except ImportError:
            self._logger.warning("SQLAlchemy not available, using mock")
            return self._mock_result(query)
        except Exception as exc:
            self._logger.exception("Query execution failed", error=str(exc))
            raise

    def _mock_result(self, query: str) -> list[dict[str, Any]]:
        """Return mock results when no real database is configured."""
        return [
            {
                "id": 1,
                "result": f"Mock result for: {query[:50]}",
                "note": "No database configured",
            }
        ]
