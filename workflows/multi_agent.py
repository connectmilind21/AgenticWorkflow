"""
Multi-Agent Workflow - collaborative execution across multiple specialized agents.
"""

from __future__ import annotations

import time
from typing import Any

import structlog

from workflows.base import BaseWorkflow, WorkflowResult, WorkflowStatus

logger = structlog.get_logger(__name__)


class MultiAgentWorkflow(BaseWorkflow):
    """
    Orchestrates collaboration between multiple specialized agents.

    Patterns:
    - Pipeline: agent A output → agent B input → agent C input
    - Debate: agents critique each other's outputs iteratively
    - Voting: multiple agents produce outputs, best is selected
    - Specialization: tasks routed to most suitable agent
    """

    def __init__(
        self,
        name: str,
        description: str = "",
        collaboration_mode: str = "pipeline",
        max_rounds: int = 3,
        max_retries: int = 2,
    ) -> None:
        super().__init__(name=name, description=description, max_retries=max_retries)
        self.collaboration_mode = collaboration_mode
        self.max_rounds = max_rounds

    def execute(
        self, context: dict[str, Any] | None = None
    ) -> WorkflowResult:
        """
        Execute the multi-agent workflow.

        Args:
            context: Initial context and task description.

        Returns:
            WorkflowResult with collaborative outputs.
        """
        start_time = time.time()
        self.status = WorkflowStatus.RUNNING
        ctx: dict[str, Any] = dict(context or {})

        self._logger.info(
            "Starting multi-agent workflow",
            mode=self.collaboration_mode,
            agents=list(self._agents.keys()),
        )

        mode_handlers = {
            "pipeline": self._run_pipeline,
            "debate": self._run_debate,
            "voting": self._run_voting,
        }

        handler = mode_handlers.get(self.collaboration_mode, self._run_pipeline)

        try:
            outputs, errors, steps_succeeded, steps_failed = handler(ctx)
        except Exception as exc:
            self.status = WorkflowStatus.FAILED
            return self._create_result(
                status=WorkflowStatus.FAILED,
                outputs={},
                errors=[str(exc)],
                start_time=start_time,
            )

        final_status = WorkflowStatus.PARTIAL if steps_failed > 0 else WorkflowStatus.SUCCESS
        self.status = final_status

        self._logger.info(
            "Multi-agent workflow complete",
            mode=self.collaboration_mode,
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
            metadata={"collaboration_mode": self.collaboration_mode},
        )

    def _run_pipeline(
        self, context: dict[str, Any]
    ) -> tuple[dict[str, Any], list[str], int, int]:
        """Run agents in a pipeline: each agent's output feeds the next."""
        outputs: dict[str, Any] = {}
        errors: list[str] = []
        steps_succeeded = 0
        steps_failed = 0
        task = context.get("task", "")
        current_context = dict(context)

        agent_list = list(self._agents.values())

        for agent in agent_list:
            try:
                result = agent.run(task, current_context)
                step_output = result.output if hasattr(result, "output") else result
                outputs[agent.name] = step_output
                current_context[f"{agent.name}_output"] = step_output
                current_context["previous_output"] = step_output
                steps_succeeded += 1
                self._logger.info("Pipeline step complete", agent=agent.name)
            except Exception as exc:
                steps_failed += 1
                errors.append(f"{agent.name}: {exc}")
                self._logger.warning("Pipeline step failed", agent=agent.name, error=str(exc))

        return outputs, errors, steps_succeeded, steps_failed

    def _run_debate(
        self, context: dict[str, Any]
    ) -> tuple[dict[str, Any], list[str], int, int]:
        """Run agents in debate mode: they iteratively critique each other."""
        outputs: dict[str, Any] = {}
        errors: list[str] = []
        steps_succeeded = 0
        steps_failed = 0
        task = context.get("task", "")
        agent_list = list(self._agents.values())
        current_output: Any = None

        for round_idx in range(self.max_rounds):
            self._logger.info("Debate round", round=round_idx + 1)
            round_outputs: dict[str, Any] = {}

            for agent in agent_list:
                try:
                    round_context = {
                        **context,
                        "round": round_idx + 1,
                        "current_proposal": current_output,
                        "artifact": current_output,
                    }
                    result = agent.run(task, round_context)
                    step_output = result.output if hasattr(result, "output") else result
                    round_outputs[agent.name] = step_output
                    steps_succeeded += 1
                except Exception as exc:
                    steps_failed += 1
                    errors.append(str(exc))

            outputs[f"round_{round_idx + 1}"] = round_outputs
            if round_outputs:
                current_output = list(round_outputs.values())[-1]

        return outputs, errors, steps_succeeded, steps_failed

    def _run_voting(
        self, context: dict[str, Any]
    ) -> tuple[dict[str, Any], list[str], int, int]:
        """Run all agents independently and select the best output."""
        outputs: dict[str, Any] = {}
        errors: list[str] = []
        steps_succeeded = 0
        steps_failed = 0
        task = context.get("task", "")
        agent_results: dict[str, Any] = {}

        for agent in self._agents.values():
            try:
                result = agent.run(task, context)
                step_output = result.output if hasattr(result, "output") else result
                agent_results[agent.name] = step_output
                steps_succeeded += 1
            except Exception as exc:
                steps_failed += 1
                errors.append(f"{agent.name}: {exc}")

        outputs["all_results"] = agent_results
        outputs["winner"] = self._select_best(agent_results)

        return outputs, errors, steps_succeeded, steps_failed

    def _select_best(self, results: dict[str, Any]) -> Any:
        """Select the best result (by output length as a proxy)."""
        if not results:
            return None
        best_key = max(results, key=lambda k: len(str(results[k])))
        return results[best_key]
