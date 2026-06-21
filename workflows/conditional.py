"""
Conditional Workflow - executes steps based on evaluated conditions.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

import structlog

from workflows.base import BaseWorkflow, WorkflowResult, WorkflowStatus

logger = structlog.get_logger(__name__)


class ConditionalBranch:
    """Represents a conditional execution branch."""

    def __init__(
        self,
        condition: Callable[[dict[str, Any]], bool],
        steps: list[Any],
        name: str = "",
    ) -> None:
        self.condition = condition
        self.steps = steps
        self.name = name or f"branch_{id(self)}"


class ConditionalWorkflow(BaseWorkflow):
    """
    Workflow with conditional branching based on runtime context.

    Supports:
    - If/else branches
    - Multiple condition evaluation
    - Dynamic routing based on agent outputs
    """

    def __init__(
        self,
        name: str,
        description: str = "",
        max_retries: int = 2,
    ) -> None:
        super().__init__(name=name, description=description, max_retries=max_retries)
        self._branches: list[ConditionalBranch] = []
        self._default_steps: list[Any] = []

    def add_branch(
        self,
        condition: Callable[[dict[str, Any]], bool],
        steps: list[Any],
        name: str = "",
    ) -> None:
        """Add a conditional branch."""
        self._branches.append(ConditionalBranch(condition=condition, steps=steps, name=name))

    def set_default(self, steps: list[Any]) -> None:
        """Set default (else) steps."""
        self._default_steps = steps

    def execute(
        self, context: dict[str, Any] | None = None
    ) -> WorkflowResult:
        """
        Execute workflow with conditional branching.

        Args:
            context: Execution context used to evaluate conditions.

        Returns:
            WorkflowResult with outputs from the executed branch.
        """
        start_time = time.time()
        self.status = WorkflowStatus.RUNNING
        ctx: dict[str, Any] = dict(context or {})
        outputs: dict[str, Any] = {}
        errors: list[str] = []
        steps_succeeded = 0
        steps_failed = 0

        self._logger.info("Starting conditional workflow")

        # Execute pre-condition steps
        for step in self._steps:
            try:
                output = self._execute_step(step, ctx)
                outputs[step.id] = output
                ctx[f"{step.id}_output"] = output
                steps_succeeded += 1
            except Exception as exc:
                steps_failed += 1
                errors.append(str(exc))
                if step.required:
                    self.status = WorkflowStatus.FAILED
                    return self._create_result(
                        status=WorkflowStatus.FAILED,
                        outputs=outputs,
                        errors=errors,
                        start_time=start_time,
                        steps_succeeded=steps_succeeded,
                        steps_failed=steps_failed,
                    )

        # Evaluate branches and execute the first matching one
        executed_branch = None
        for branch in self._branches:
            try:
                if branch.condition(ctx):
                    self._logger.info("Executing branch", branch=branch.name)
                    executed_branch = branch.name
                    for step in branch.steps:
                        try:
                            output = self._execute_step(step, ctx)
                            outputs[step.id] = output
                            ctx[f"{step.id}_output"] = output
                            steps_succeeded += 1
                        except Exception as exc:
                            steps_failed += 1
                            errors.append(str(exc))
                    break
            except Exception as exc:
                self._logger.warning(
                    "Condition evaluation error",
                    branch=branch.name,
                    error=str(exc),
                )

        if executed_branch is None and self._default_steps:
            self._logger.info("Executing default branch")
            for step in self._default_steps:
                try:
                    output = self._execute_step(step, ctx)
                    outputs[step.id] = output
                    steps_succeeded += 1
                except Exception as exc:
                    steps_failed += 1
                    errors.append(str(exc))

        final_status = WorkflowStatus.PARTIAL if steps_failed > 0 else WorkflowStatus.SUCCESS
        self.status = final_status

        return self._create_result(
            status=final_status,
            outputs=outputs,
            errors=errors,
            start_time=start_time,
            steps_succeeded=steps_succeeded,
            steps_failed=steps_failed,
            metadata={"executed_branch": executed_branch},
        )

    def _execute_step(self, step: Any, context: dict[str, Any]) -> Any:
        """Execute a workflow step."""
        agent_name = getattr(step, "agent_name", None)
        agent = self._agents.get(agent_name) if agent_name else None

        if agent:
            task = getattr(step, "task", "") or context.get("task", "")
            inputs = getattr(step, "inputs", {})
            result = agent.run(task, {**context, **inputs})
            return result.output if hasattr(result, "output") else result

        return {"step": getattr(step, "id", "unknown"), "status": "completed"}
