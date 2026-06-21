"""
Planner Agent - decomposes complex goals into structured execution plans.
"""

from __future__ import annotations

import time
from typing import Any

import structlog

from agents.base import AgentResult, AgentStatus, BaseAgent

logger = structlog.get_logger(__name__)


class Plan(dict):
    """Represents an execution plan with goals, steps, and dependencies."""

    @classmethod
    def create(
        cls,
        goal: str,
        steps: list[dict[str, Any]],
        dependencies: dict[str, list[str]] | None = None,
    ) -> Plan:
        instance = cls()
        instance["goal"] = goal
        instance["steps"] = steps
        instance["dependencies"] = dependencies or {}
        instance["total_steps"] = len(steps)
        return instance


class PlannerAgent(BaseAgent):
    """
    Agent responsible for decomposing high-level goals into executable plans.

    The PlannerAgent analyzes a task and produces a structured plan with:
    - Clear, actionable steps
    - Dependencies between steps
    - Resource requirements
    - Success criteria
    """

    def __init__(
        self,
        tools: list | None = None,
        memory: Any | None = None,
        max_iterations: int = 5,
        verbose: bool = False,
    ) -> None:
        super().__init__(
            name="PlannerAgent",
            description=(
                "Decomposes complex goals into structured, executable plans "
                "with clear steps and dependencies."
            ),
            tools=tools,
            memory=memory,
            max_iterations=max_iterations,
            verbose=verbose,
        )

    def run(self, task: str, context: dict[str, Any] | None = None) -> AgentResult:
        """
        Generate an execution plan for the given task.

        Args:
            task: High-level goal or task description.
            context: Optional context (e.g., available tools, constraints).

        Returns:
            AgentResult with a Plan as the output.
        """
        start_time = time.time()
        self.status = AgentStatus.RUNNING
        ctx = context or {}

        self._logger.info("Starting planning", task=task)

        try:
            plan = self._generate_plan(task, ctx)

            if self.memory:
                self.memory.add({"role": "planner", "content": str(plan), "task": task})

            self.status = AgentStatus.SUCCESS
            self._logger.info("Planning complete", steps=plan["total_steps"])

            return self._create_result(
                status=AgentStatus.SUCCESS,
                output=plan,
                start_time=start_time,
                iterations=1,
                metadata={"task": task, "step_count": plan["total_steps"]},
            )
        except Exception as exc:
            self.status = AgentStatus.FAILED
            self._logger.exception("Planning failed", error=str(exc))
            return self._create_result(
                status=AgentStatus.FAILED,
                error=str(exc),
                start_time=start_time,
            )

    def _generate_plan(self, task: str, context: dict[str, Any]) -> Plan:
        """Generate a structured plan for the task."""
        available_tools = context.get("available_tools", self.get_tool_names())

        steps = self._decompose_task(task, available_tools)

        return Plan.create(
            goal=task,
            steps=steps,
            dependencies=self._infer_dependencies(steps),
        )

    def _decompose_task(
        self, task: str, available_tools: list[str]
    ) -> list[dict[str, Any]]:
        """Break a task into ordered, concrete steps."""
        keywords = task.lower()
        steps: list[dict[str, Any]] = []

        if any(w in keywords for w in ["research", "search", "find", "look up"]):
            steps.append(
                {
                    "id": "step_1",
                    "name": "Research",
                    "description": f"Gather relevant information for: {task}",
                    "agent": "ResearchAgent",
                    "tools": ["web_search"] if "web_search" in available_tools else [],
                    "inputs": {"query": task},
                    "outputs": ["research_results"],
                }
            )

        if any(w in keywords for w in ["analyze", "analysis", "data", "statistics"]):
            step_id = f"step_{len(steps) + 1}"
            steps.append(
                {
                    "id": step_id,
                    "name": "Analysis",
                    "description": f"Analyze gathered data for: {task}",
                    "agent": "DataAnalysisAgent",
                    "tools": ["python_exec"] if "python_exec" in available_tools else [],
                    "inputs": {"data": "$research_results"},
                    "outputs": ["analysis_results"],
                }
            )

        if any(w in keywords for w in ["code", "implement", "develop", "build", "write"]):
            step_id = f"step_{len(steps) + 1}"
            steps.append(
                {
                    "id": step_id,
                    "name": "Implementation",
                    "description": f"Implement solution for: {task}",
                    "agent": "CodingAgent",
                    "tools": ["python_exec"] if "python_exec" in available_tools else [],
                    "inputs": {"specification": task},
                    "outputs": ["code_artifacts"],
                }
            )

        if any(w in keywords for w in ["review", "check", "verify", "validate"]):
            step_id = f"step_{len(steps) + 1}"
            steps.append(
                {
                    "id": step_id,
                    "name": "Review",
                    "description": f"Review and validate output for: {task}",
                    "agent": "ReviewerAgent",
                    "tools": [],
                    "inputs": {"artifacts": "$code_artifacts"},
                    "outputs": ["review_results"],
                }
            )

        if not steps:
            steps.append(
                {
                    "id": "step_1",
                    "name": "Execute",
                    "description": f"Execute task: {task}",
                    "agent": "ExecutionAgent",
                    "tools": available_tools,
                    "inputs": {"task": task},
                    "outputs": ["execution_results"],
                }
            )

        return steps

    def _infer_dependencies(
        self, steps: list[dict[str, Any]]
    ) -> dict[str, list[str]]:
        """Infer sequential dependencies between steps."""
        deps: dict[str, list[str]] = {}
        for i, step in enumerate(steps):
            if i > 0:
                deps[step["id"]] = [steps[i - 1]["id"]]
            else:
                deps[step["id"]] = []
        return deps
