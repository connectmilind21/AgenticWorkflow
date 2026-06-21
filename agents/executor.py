"""
Execution Agent - executes tasks and manages tool invocations.
"""

from __future__ import annotations

import time
from typing import Any

import structlog

from agents.base import AgentResult, AgentStatus, BaseAgent

logger = structlog.get_logger(__name__)


class ExecutionAgent(BaseAgent):
    """
    Agent that executes concrete tasks using available tools.

    The ExecutionAgent:
    - Runs tool chains
    - Manages execution state
    - Handles retries on failure
    - Reports detailed execution logs
    """

    def __init__(
        self,
        tools: list | None = None,
        memory: Any | None = None,
        max_iterations: int = 10,
        verbose: bool = False,
    ) -> None:
        super().__init__(
            name="ExecutionAgent",
            description=(
                "Executes concrete tasks using available tools, managing "
                "execution state and handling errors with retries."
            ),
            tools=tools,
            memory=memory,
            max_iterations=max_iterations,
            verbose=verbose,
        )

    def run(self, task: str, context: dict[str, Any] | None = None) -> AgentResult:
        """
        Execute the given task using available tools.

        Args:
            task: Task to execute.
            context: Execution context with parameters and state.

        Returns:
            AgentResult with execution logs and output.
        """
        start_time = time.time()
        self.status = AgentStatus.RUNNING
        ctx = context or {}

        self._logger.info("Starting execution", task=task)

        execution_log: list[dict[str, Any]] = []
        iterations = 0

        try:
            steps = ctx.get("steps") or self._plan_steps(task, ctx)

            for step in steps:
                if iterations >= self.max_iterations:
                    break

                step_result = self._execute_step(step, ctx)
                execution_log.append(step_result)
                iterations += 1

                if not step_result.get("success", True):
                    if step.get("required", True):
                        raise RuntimeError(
                            f"Required step failed: {step_result.get('error', 'unknown')}"
                        )

            final_output = self._consolidate_output(execution_log)

            if self.memory:
                self.memory.add(
                    {"role": "executor", "content": str(final_output), "task": task}
                )

            self.status = AgentStatus.SUCCESS
            self._logger.info(
                "Execution complete",
                steps=len(execution_log),
                iterations=iterations,
            )

            return self._create_result(
                status=AgentStatus.SUCCESS,
                output={
                    "result": final_output,
                    "execution_log": execution_log,
                    "steps_executed": iterations,
                },
                start_time=start_time,
                iterations=iterations,
            )

        except Exception as exc:
            self.status = AgentStatus.FAILED
            self._logger.exception("Execution failed", error=str(exc))
            return self._create_result(
                status=AgentStatus.FAILED,
                error=str(exc),
                start_time=start_time,
                iterations=iterations,
            )

    def _plan_steps(
        self, task: str, context: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Create execution steps from the task description."""
        tool_names = self.get_tool_names()
        steps: list[dict[str, Any]] = []

        if "search" in task.lower() and "web_search" in tool_names:
            steps.append(
                {"id": "search", "tool": "web_search", "input": task, "required": False}
            )
        if "file" in task.lower() and "file_operations" in tool_names:
            steps.append(
                {"id": "file_op", "tool": "file_operations", "input": task, "required": False}
            )

        if not steps:
            steps.append(
                {
                    "id": "execute",
                    "tool": tool_names[0] if tool_names else None,
                    "input": task,
                    "required": False,
                }
            )

        return steps

    def _execute_step(
        self, step: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute a single step."""
        tool_name = step.get("tool")
        input_data = step.get("input", "")
        step_id = step.get("id", "unknown")

        if not tool_name:
            return {
                "step_id": step_id,
                "tool": None,
                "success": True,
                "output": f"Completed: {input_data}",
            }

        tool = self._get_tool(tool_name)
        if not tool:
            return {
                "step_id": step_id,
                "tool": tool_name,
                "success": False,
                "error": f"Tool '{tool_name}' not available",
            }

        try:
            output = tool.run(input_data)
            return {
                "step_id": step_id,
                "tool": tool_name,
                "success": True,
                "output": output,
            }
        except Exception as exc:
            return {
                "step_id": step_id,
                "tool": tool_name,
                "success": False,
                "error": str(exc),
            }

    def _get_tool(self, tool_name: str) -> Any | None:
        """Retrieve a tool by name."""
        for tool in self.tools:
            if getattr(tool, "name", None) == tool_name:
                return tool
        return None

    def _consolidate_output(
        self, execution_log: list[dict[str, Any]]
    ) -> Any:
        """Consolidate outputs from all execution steps."""
        outputs = [
            step.get("output")
            for step in execution_log
            if step.get("success") and step.get("output") is not None
        ]
        if not outputs:
            return None
        if len(outputs) == 1:
            return outputs[0]
        return outputs
