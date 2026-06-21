"""
Coordinator Agent - orchestrates multi-agent workflows.
"""

from __future__ import annotations

import time
from typing import Any

import structlog

from agents.base import AgentResult, AgentStatus, BaseAgent

logger = structlog.get_logger(__name__)


class CoordinatorAgent(BaseAgent):
    """
    Agent that orchestrates other agents to complete complex multi-step tasks.

    The CoordinatorAgent:
    - Routes tasks to appropriate sub-agents
    - Manages data flow between agents
    - Aggregates results
    - Handles failures and retries
    """

    def __init__(
        self,
        sub_agents: list[BaseAgent] | None = None,
        tools: list | None = None,
        memory: Any | None = None,
        max_iterations: int = 20,
        verbose: bool = False,
    ) -> None:
        super().__init__(
            name="CoordinatorAgent",
            description=(
                "Orchestrates multi-agent workflows by routing tasks, managing "
                "data flow, and aggregating results from specialized sub-agents."
            ),
            tools=tools,
            memory=memory,
            max_iterations=max_iterations,
            verbose=verbose,
        )
        self.sub_agents: dict[str, BaseAgent] = {}
        for agent in (sub_agents or []):
            self.register_agent(agent)

    def register_agent(self, agent: BaseAgent) -> None:
        """Register a sub-agent for use in orchestration."""
        self.sub_agents[agent.name] = agent
        self._logger.info("Agent registered", agent_name=agent.name)

    def run(self, task: str, context: dict[str, Any] | None = None) -> AgentResult:
        """
        Coordinate agents to complete the given task.

        Args:
            task: High-level task to complete.
            context: Context with workflow plan or parameters.

        Returns:
            AgentResult with aggregated output.
        """
        start_time = time.time()
        self.status = AgentStatus.RUNNING
        ctx = context or {}

        self._logger.info(
            "Coordinator starting",
            task=task,
            agents=list(self.sub_agents.keys()),
        )

        agent_results: dict[str, Any] = {}
        iterations = 0

        try:
            workflow = ctx.get("workflow") or self._build_workflow(task, ctx)
            shared_context = dict(ctx)

            for step in workflow:
                if iterations >= self.max_iterations:
                    self._logger.warning("Max iterations reached")
                    break

                agent_name = step.get("agent")
                step_task = step.get("task", task)
                step_ctx = self._build_step_context(step, shared_context, agent_results)

                agent = self.sub_agents.get(agent_name) if agent_name else None

                if agent:
                    self._logger.info(
                        "Dispatching to agent",
                        agent=agent_name,
                        step=step.get("id"),
                    )
                    result = agent.run(step_task, step_ctx)
                    agent_results[step.get("id", agent_name)] = {
                        "agent": agent_name,
                        "status": result.status.value,
                        "output": result.output,
                        "error": result.error,
                    }
                    shared_context[f"{step.get('id', agent_name)}_result"] = result.output
                else:
                    self._logger.warning("Agent not found", agent=agent_name)
                    agent_results[step.get("id", "unknown")] = {
                        "error": f"Agent '{agent_name}' not registered",
                        "status": "skipped",
                    }

                iterations += 1

            final_output = self._aggregate_results(agent_results, task)

            if self.memory:
                self.memory.add(
                    {"role": "coordinator", "content": str(final_output), "task": task}
                )

            self.status = AgentStatus.SUCCESS
            self._logger.info(
                "Coordination complete",
                agents_used=len(agent_results),
                iterations=iterations,
            )

            return self._create_result(
                status=AgentStatus.SUCCESS,
                output=final_output,
                start_time=start_time,
                iterations=iterations,
                metadata={"agents_used": list(agent_results.keys())},
            )

        except Exception as exc:
            self.status = AgentStatus.FAILED
            self._logger.exception("Coordination failed", error=str(exc))
            return self._create_result(
                status=AgentStatus.FAILED,
                error=str(exc),
                start_time=start_time,
                iterations=iterations,
            )

    def _build_workflow(
        self, task: str, context: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Build a default sequential workflow from available agents."""
        available = list(self.sub_agents.keys())
        steps: list[dict[str, Any]] = []

        agent_order = [
            "PlannerAgent",
            "ResearchAgent",
            "DataAnalysisAgent",
            "CodingAgent",
            "ReviewerAgent",
            "CriticAgent",
            "ExecutionAgent",
        ]

        for i, agent_name in enumerate(agent_order):
            if agent_name in available:
                steps.append(
                    {
                        "id": f"step_{i + 1}",
                        "agent": agent_name,
                        "task": task,
                        "required": False,
                    }
                )

        return steps

    def _build_step_context(
        self,
        step: dict[str, Any],
        shared_context: dict[str, Any],
        previous_results: dict[str, Any],
    ) -> dict[str, Any]:
        """Build context for a specific step, injecting relevant previous outputs."""
        step_ctx = dict(shared_context)
        step_ctx["previous_results"] = previous_results

        input_mappings = step.get("inputs", {})
        for key, value_ref in input_mappings.items():
            if isinstance(value_ref, str) and value_ref.startswith("$"):
                ref_key = value_ref[1:]
                if ref_key in shared_context:
                    step_ctx[key] = shared_context[ref_key]

        return step_ctx

    def _aggregate_results(
        self,
        agent_results: dict[str, Any],
        task: str,
    ) -> dict[str, Any]:
        """Aggregate results from all sub-agents."""
        successful = {
            k: v for k, v in agent_results.items() if v.get("status") == "success"
        }
        failed = {
            k: v for k, v in agent_results.items() if v.get("status") == "failed"
        }

        return {
            "task": task,
            "total_steps": len(agent_results),
            "successful_steps": len(successful),
            "failed_steps": len(failed),
            "results": agent_results,
            "summary": (
                f"Completed {len(successful)}/{len(agent_results)} steps successfully"
                f" for task: '{task}'"
            ),
        }
