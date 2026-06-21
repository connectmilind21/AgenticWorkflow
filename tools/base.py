"""
Base tool implementation for the Agentic Workflow Framework.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any

import structlog
from pydantic import BaseModel, Field


class ToolStatus(StrEnum):
    """Tool execution status."""

    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    DISABLED = "disabled"


class ToolResult(BaseModel):
    """Result of a tool execution."""

    tool_name: str
    status: ToolStatus
    output: Any | None = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class BaseTool(ABC):
    """
    Abstract base class for all tools in the framework.

    Tools are callable units that agents use to interact with the world.
    Each tool must implement the `run` method.
    """

    def __init__(
        self,
        name: str,
        description: str,
        enabled: bool = True,
    ) -> None:
        self.name = name
        self.description = description
        self.enabled = enabled
        self._logger = structlog.get_logger(__name__).bind(tool_name=name)

    @abstractmethod
    def run(self, input_data: Any, **kwargs: Any) -> Any:
        """
        Execute the tool with the given input.

        Args:
            input_data: Tool-specific input data.
            **kwargs: Additional keyword arguments.

        Returns:
            Tool output (type depends on the specific tool).
        """

    def __call__(self, input_data: Any = None, **kwargs: Any) -> Any:
        """Allow tools to be called directly."""
        if not self.enabled:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.DISABLED,
                error=f"Tool '{self.name}' is disabled",
            )
        if input_data is None and kwargs:
            input_data = kwargs
        return self.run(input_data, **kwargs)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r}, enabled={self.enabled})"
