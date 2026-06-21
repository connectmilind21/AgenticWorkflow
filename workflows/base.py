"""
Base workflow implementation for the Agentic Workflow Framework.
"""

from __future__ import annotations

import time
import uuid
from abc import ABC, abstractmethod
from collections.abc import Callable
from enum import StrEnum
from typing import Any

import structlog
from pydantic import BaseModel, Field


class WorkflowStatus(StrEnum):
    """Workflow execution status."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PARTIAL = "partial"


class WorkflowStep(BaseModel):
    """Represents a single step within a workflow."""

    id: str
    name: str
    agent_name: str | None = None
    task: str = ""
    inputs: dict[str, Any] = Field(default_factory=dict)
    outputs: list[str] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)
    required: bool = True
    retry_count: int = 0
    max_retries: int = 2
    timeout: int | None = None
    condition: str | None = None


class WorkflowResult(BaseModel):
    """Result of a workflow execution."""

    workflow_id: str
    workflow_name: str
    status: WorkflowStatus
    steps_total: int = 0
    steps_succeeded: int = 0
    steps_failed: int = 0
    outputs: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    execution_time: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class BaseWorkflow(ABC):
    """
    Abstract base class for all workflow types.

    Workflows orchestrate the execution of agents and steps,
    managing state, dependencies, and error handling.
    """

    def __init__(
        self,
        name: str,
        description: str = "",
        max_retries: int = 3,
        retry_backoff: float = 2.0,
    ) -> None:
        self.workflow_id = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff
        self.status = WorkflowStatus.PENDING
        self._steps: list[WorkflowStep] = []
        self._agents: dict[str, Any] = {}
        self._hooks: dict[str, list[Callable]] = {
            "before_step": [],
            "after_step": [],
            "on_error": [],
        }
        self._logger = structlog.get_logger(__name__).bind(
            workflow_id=self.workflow_id,
            workflow_name=self.name,
        )

    def add_step(self, step: WorkflowStep) -> None:
        """Add a step to the workflow."""
        self._steps.append(step)

    def register_agent(self, agent: Any) -> None:
        """Register an agent for use in this workflow."""
        self._agents[agent.name] = agent

    def add_hook(self, event: str, callback: Callable) -> None:
        """Add a lifecycle hook callback."""
        if event in self._hooks:
            self._hooks[event].append(callback)

    @abstractmethod
    def execute(
        self, context: dict[str, Any] | None = None
    ) -> WorkflowResult:
        """
        Execute the workflow.

        Args:
            context: Initial context for the workflow.

        Returns:
            WorkflowResult with execution details.
        """

    def _create_result(
        self,
        status: WorkflowStatus,
        outputs: dict[str, Any],
        errors: list[str],
        start_time: float,
        steps_succeeded: int = 0,
        steps_failed: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> WorkflowResult:
        """Create a standardized WorkflowResult."""
        return WorkflowResult(
            workflow_id=self.workflow_id,
            workflow_name=self.name,
            status=status,
            steps_total=len(self._steps),
            steps_succeeded=steps_succeeded,
            steps_failed=steps_failed,
            outputs=outputs,
            errors=errors,
            execution_time=time.time() - start_time,
            metadata=metadata or {},
        )

    def _fire_hooks(self, event: str, **kwargs: Any) -> None:
        """Fire lifecycle hooks for an event."""
        for callback in self._hooks.get(event, []):
            try:
                callback(**kwargs)
            except Exception as exc:
                self._logger.warning("Hook error", event=event, error=str(exc))

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"name={self.name!r}, "
            f"steps={len(self._steps)}, "
            f"status={self.status.value!r})"
        )
