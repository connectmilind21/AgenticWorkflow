"""
Sequential Workflow - executes steps one after another.
"""

from __future__ import annotations

import time
from typing import Any

import structlog

from workflows.base import BaseWorkflow, WorkflowResult, WorkflowStatus

logger = structlog.get_logger(__name__)


class SequentialWorkflow(BaseWorkflow):
    """
    Executes workflow steps in sequential order.

    Features:
    - Ordered step execution
    - Output passing between steps
    - Retry with exponential backoff
    - Optional step skipping on failure
    """

    def __init__(
        self,
        name: str,
        description: str = "",
        max_retries: int = 3,
        stop_on_failure: bool = True,
    ) -> None:
        super().__init__(name=name, description=description, max_retries=max_retries)
        self.stop_on_failure = stop_on_failure

    def execute(
        self, context: dict[str, Any] | None = None
    ) -> WorkflowResult:
        """
        Execute all steps sequentially.

        Args:
            context: Initial context shared across all steps.

        Returns:
            WorkflowResult with step outputs and execution stats.
        """
        start_time = time.time()
        self.status = WorkflowStatus.RUNNING
        ctx: dict[str, Any] = dict(context or {})
        outputs: dict[str, Any] = {}
        errors: list[str] = []
        steps_succeeded = 0
        steps_failed = 0

        self._logger.info("Starting sequential workflow", total_steps=len(self._steps))

        for step in self._steps:
            self._fire_hooks("before_step", step=step, context=ctx)

            attempt = 0
            step_success = False

            while attempt <= step.max_retries and not step_success:
                attempt += 1
                try:
                    step_output = self._execute_step(step, ctx)
                    outputs[step.id] = step_output
                    ctx[f"{step.id}_output"] = step_output
                    steps_succeeded += 1
                    step_success = True
                    self._logger.info(
                        "Step completed",
                        step_id=step.id,
                        attempt=attempt,
                    )
                    self._fire_hooks("after_step", step=step, output=step_output)

                except Exception as exc:
                    error_msg = f"Step '{step.id}' attempt {attempt} failed: {exc}"
                    self._logger.warning(error_msg)

                    if attempt <= step.max_retries:
                        wait = self.retry_backoff ** (attempt - 1)
                        time.sleep(min(wait, 10))
                    else:
                        steps_failed += 1
                        errors.append(error_msg)
                        self._fire_hooks("on_error", step=step, error=exc)

                        if step.required and self.stop_on_failure:
                            self.status = WorkflowStatus.FAILED
                            return self._create_result(
                                status=WorkflowStatus.FAILED,
                                outputs=outputs,
                                errors=errors,
                                start_time=start_time,
                                steps_succeeded=steps_succeeded,
                                steps_failed=steps_failed,
                            )

        has_failures = steps_failed > 0
        final_status = WorkflowStatus.PARTIAL if has_failures else WorkflowStatus.SUCCESS
        self.status = final_status

        self._logger.info(
            "Sequential workflow complete",
            succeeded=steps_succeeded,
            failed=steps_failed,
        )

        return self._create_result(
            status=final_status,
            outputs=outputs,
            errors=errors,
            start_time=start_time,
            steps_succeeded=steps_succeeded,
            steps_failed=steps_failed,
        )

    def _execute_step(
        self, step: Any, context: dict[str, Any]
    ) -> Any:
        """Execute a single workflow step."""
        agent = self._agents.get(step.agent_name) if step.agent_name else None

        if step.agent_name and not agent:
            raise RuntimeError(f"Agent '{step.agent_name}' is not registered in this workflow.")

        if agent:
            step_context = {**context, **step.inputs}
            result = agent.run(step.task or context.get("task", ""), step_context)
            return result.output if hasattr(result, "output") else result

        if step.inputs.get("function"):
            func = step.inputs["function"]
            return func(context)

        return {"step": step.id, "status": "completed", "context": context}
