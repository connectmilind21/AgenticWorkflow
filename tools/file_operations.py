"""
File Operations Tool - reads, writes, and manages files.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog

from tools.base import BaseTool

logger = structlog.get_logger(__name__)

ALLOWED_EXTENSIONS = {".txt", ".md", ".json", ".csv", ".yaml", ".yml", ".py", ".html"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


class FileOperationsTool(BaseTool):
    """
    Tool for reading, writing, listing, and managing files.

    Security: Only operates within the configured base directory.
    """

    def __init__(
        self,
        base_dir: str | None = None,
        allowed_extensions: set[str] | None = None,
        max_file_size_bytes: int = MAX_FILE_SIZE_BYTES,
        enabled: bool = True,
    ) -> None:
        super().__init__(
            name="file_operations",
            description=(
                "Performs file operations: read, write, list, delete, and search. "
                "Operates within a configured base directory for security."
            ),
            enabled=enabled,
        )
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        self.allowed_extensions = allowed_extensions or ALLOWED_EXTENSIONS
        self.max_file_size_bytes = max_file_size_bytes

    def run(self, input_data: Any, **kwargs: Any) -> Any:
        """
        Execute a file operation.

        Args:
            input_data: Operation specification as dict or string.
                - dict: {"operation": "read|write|list|delete|search", ...}
                - str: treated as a path to read.
            **kwargs: Additional operation parameters.

        Returns:
            Operation result (str for read, list for list, bool for write/delete).
        """
        if isinstance(input_data, str):
            return self._read(input_data)

        if isinstance(input_data, dict):
            operation = input_data.get("operation", "read")
            handlers = {
                "read": lambda: self._read(input_data.get("path", "")),
                "write": lambda: self._write(
                    input_data.get("path", ""),
                    input_data.get("content", ""),
                ),
                "list": lambda: self._list(input_data.get("path", ".")),
                "delete": lambda: self._delete(input_data.get("path", "")),
                "search": lambda: self._search(
                    input_data.get("query", ""),
                    input_data.get("path", "."),
                ),
            }
            handler = handlers.get(operation)
            if handler:
                return handler()
            raise ValueError(f"Unknown file operation: {operation}")

        raise TypeError(f"Unexpected input type: {type(input_data)}")

    def _resolve_path(self, relative_path: str) -> Path:
        """Resolve and validate a path within the base directory."""
        path = (self.base_dir / relative_path).resolve()
        if not str(path).startswith(str(self.base_dir.resolve())):
            raise PermissionError(
                f"Path '{path}' is outside the allowed base directory."
            )
        return path

    def _read(self, path: str) -> str:
        """Read a file and return its content."""
        resolved = self._resolve_path(path)

        if not resolved.exists():
            raise FileNotFoundError(f"File not found: {path}")
        if resolved.is_dir():
            raise IsADirectoryError(f"Path is a directory: {path}")
        if resolved.suffix not in self.allowed_extensions:
            raise ValueError(f"Extension '{resolved.suffix}' not allowed.")
        if resolved.stat().st_size > self.max_file_size_bytes:
            raise ValueError(f"File '{path}' exceeds max size limit.")

        return resolved.read_text(encoding="utf-8")

    def _write(self, path: str, content: str) -> bool:
        """Write content to a file."""
        resolved = self._resolve_path(path)

        if resolved.suffix not in self.allowed_extensions:
            raise ValueError(f"Extension '{resolved.suffix}' not allowed.")

        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content, encoding="utf-8")
        self._logger.info("File written", path=str(resolved))
        return True

    def _list(self, path: str) -> list[dict[str, Any]]:
        """List files in a directory."""
        resolved = self._resolve_path(path)

        if not resolved.exists():
            raise FileNotFoundError(f"Directory not found: {path}")
        if not resolved.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {path}")

        entries: list[dict[str, Any]] = []
        for entry in sorted(resolved.iterdir()):
            if entry.suffix in self.allowed_extensions or entry.is_dir():
                entries.append(
                    {
                        "name": entry.name,
                        "path": str(entry.relative_to(self.base_dir)),
                        "type": "directory" if entry.is_dir() else "file",
                        "size": entry.stat().st_size if entry.is_file() else None,
                    }
                )
        return entries

    def _delete(self, path: str) -> bool:
        """Delete a file."""
        resolved = self._resolve_path(path)

        if not resolved.exists():
            raise FileNotFoundError(f"File not found: {path}")
        if resolved.is_dir():
            raise IsADirectoryError(f"Cannot delete directory: {path}")

        resolved.unlink()
        self._logger.info("File deleted", path=str(resolved))
        return True

    def _search(self, query: str, path: str) -> list[dict[str, Any]]:
        """Search for files containing the given query string."""
        resolved = self._resolve_path(path)
        results: list[dict[str, Any]] = []

        for file_path in resolved.rglob("*"):
            if (
                file_path.is_file()
                and file_path.suffix in self.allowed_extensions
                and file_path.stat().st_size <= self.max_file_size_bytes
            ):
                try:
                    content = file_path.read_text(encoding="utf-8")
                    if query.lower() in content.lower():
                        results.append(
                            {
                                "path": str(file_path.relative_to(self.base_dir)),
                                "match_count": content.lower().count(query.lower()),
                            }
                        )
                except (UnicodeDecodeError, PermissionError):
                    continue

        return results
