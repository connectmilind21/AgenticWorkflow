"""
Parallel Workflow - executes independent steps concurrently.
"""

from __future__ import annotations

import time
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from typing import Any

import structlog

from workflows.base import BaseWorkflow, WorkflowResult, WorkflowStatus, WorkflowStep

logger = structlog.get_logger(__name__)


class ParallelWorkflow(BaseWorkflow):
    """
    Executes independent workflow steps concurrently using a thread pool.

    Features:
    - Concurrent step execution
    - Configurable parallelism
    - Dependency resolution (sequential batches for dependent steps)
    - Timeout support
    """

    def __init__(
        self,
        name: str,
        description: str = "",
        max_workers: int = 5,
        max_retries: int = 2,
    ) -> None:
        super().__init__(name=name, description=description, max_retries=max_retries)
        self.max_workers = max_workers

    def execute(
        self, context: dict[str, Any] | None = None
    ) -> WorkflowResult:
        """
        Execute steps in parallel batches based on dependencies.

        Args:
            context: Initial context shared across all steps.

        Returns:
            WorkflowResult with outputs from all steps.
        """
        start_time = time.time()
        self.status = WorkflowStatus.RUNNING
        ctx: dict[str, Any] = dict(context or {})
        outputs: dict[str, Any] = {}
        errors: list[str] = []
        steps_succeeded = 0
        steps_failed = 0

        self._logger.info(
            "Starting parallel workflow",
            total_steps=len(self._steps),
            max_workers=self.max_workers,
        )

        batches = self._resolve_batches(self._steps)

        for batch_idx, batch in enumerate(batches):
            self._logger.info(
                "Executing batch",
                batch=batch_idx + 1,
                batch_size=len(batch),
            )

            batch_results = self._run_batch(batch, ctx)

            for step_id, result in batch_results.items():
                if result.get("error"):
                    steps_failed += 1
                    errors.append(f"Step '{step_id}': {result['error']}")
                else:
                    steps_succeeded += 1
                    outputs[step_id] = result.get("output")
                    ctx[f"{step_id}_output"] = result.get("output")

        has_failures = steps_failed > 0
        final_status = WorkflowStatus.PARTIAL if has_failures else WorkflowStatus.SUCCESS
        self.status = final_status

        self._logger.info(
            "Parallel workflow complete",
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

    def _resolve_batches(
        self, steps: list[WorkflowStep]
    ) -> list[list[WorkflowStep]]:
        """Group steps into parallel batches based on dependencies."""
        completed: set[str] = set()
        remaining = list(steps)
        batches: list[list[WorkflowStep]] = []

        while remaining:
            ready = [
                step
                for step in remaining
                if all(dep in completed for dep in step.depends_on)
            ]
            if not ready:
                # If nothing is ready, add remaining as final batch
                ready = remaining

            batches.append(ready)
            for step in ready:
                completed.add(step.id)
                remaining.remove(step)

        return batches

    def _run_batch(
        self,
        batch: list[WorkflowStep],
        context: dict[str, Any],
    ) -> dict[str, dict[str, Any]]:
        """Run a batch of steps concurrently."""
        results: dict[str, dict[str, Any]] = {}

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_step: dict[Future, WorkflowStep] = {
                executor.submit(self._execute_step, step, dict(context)): step
                for step in batch
            }

            for future in as_completed(future_to_step):
                step = future_to_step[future]
                try:
                    output = future.result(
                        timeout=step.timeout or 300
                    )
                    results[step.id] = {"output": output, "error": None}
                except Exception as exc:
                    results[step.id] = {"output": None, "error": str(exc)}

        return results

    def _execute_step(
        self, step: WorkflowStep, context: dict[str, Any]
    ) -> Any:
        """Execute a single step (runs in thread pool)."""
        agent = self._agents.get(step.agent_name) if step.agent_name else None

        if agent:
            step_context = {**context, **step.inputs}
            result = agent.run(step.task or context.get("task", ""), step_context)
            return result.output if hasattr(result, "output") else result

        return {"step": step.id, "status": "completed"}
