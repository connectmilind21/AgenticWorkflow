"""
Base agent implementation for the Agentic Workflow Framework.
"""

from __future__ import annotations

import time
import uuid
from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class AgentStatus(StrEnum):
    """Agent execution status."""

    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentResult(BaseModel):
    """Result of an agent execution."""

    agent_id: str
    agent_name: str
    status: AgentStatus
    output: Any | None = None
    error: str | None = None
    execution_time: float = 0.0
    iterations: int = 0
    token_usage: dict[str, int] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class BaseAgent(ABC):
    """
    Abstract base class for all agents in the framework.

    Provides common functionality including:
    - Tool management
    - Memory integration
    - Execution tracking
    - Error handling
    - Observability
    """

    def __init__(
        self,
        name: str,
        description: str,
        tools: list | None = None,
        memory: Any | None = None,
        max_iterations: int = 10,
        max_execution_time: int = 300,
        verbose: bool = False,
    ) -> None:
        self.agent_id = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.tools = tools or []
        self.memory = memory
        self.max_iterations = max_iterations
        self.max_execution_time = max_execution_time
        self.verbose = verbose
        self.status = AgentStatus.IDLE
        self._logger = structlog.get_logger(__name__).bind(
            agent_id=self.agent_id,
            agent_name=self.name,
        )

    @abstractmethod
    def run(self, task: str, context: dict[str, Any] | None = None) -> AgentResult:
        """
        Execute the agent on a given task.

        Args:
            task: The task description or instruction.
            context: Optional context dictionary with additional information.

        Returns:
            AgentResult containing execution details and output.
        """

    def _create_result(
        self,
        status: AgentStatus,
        output: Any | None = None,
        error: str | None = None,
        start_time: float | None = None,
        iterations: int = 0,
        token_usage: dict[str, int] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AgentResult:
        """Helper to create a standardized AgentResult."""
        execution_time = time.time() - start_time if start_time else 0.0
        return AgentResult(
            agent_id=self.agent_id,
            agent_name=self.name,
            status=status,
            output=output,
            error=error,
            execution_time=execution_time,
            iterations=iterations,
            token_usage=token_usage or {},
            metadata=metadata or {},
        )

    def get_tool_names(self) -> list[str]:
        """Return list of available tool names."""
        return [tool.name for tool in self.tools if hasattr(tool, "name")]

    def add_tool(self, tool: Any) -> None:
        """Add a tool to the agent."""
        self.tools.append(tool)
        self._logger.info("Tool added", tool_name=getattr(tool, "name", str(tool)))

    def set_memory(self, memory: Any) -> None:
        """Set the memory backend for this agent."""
        self.memory = memory

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r}, id={self.agent_id!r})"
