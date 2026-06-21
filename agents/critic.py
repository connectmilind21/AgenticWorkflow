"""
Critic Agent - provides adversarial critiques to improve quality.
"""

from __future__ import annotations

import time
from typing import Any

import structlog

from agents.base import AgentResult, AgentStatus, BaseAgent

logger = structlog.get_logger(__name__)


class CriticAgent(BaseAgent):
    """
    Agent that provides adversarial critiques to identify weaknesses and gaps.

    The CriticAgent challenges outputs by:
    - Identifying logical flaws
    - Spotting missing edge cases
    - Questioning assumptions
    - Suggesting alternatives
    """

    def __init__(
        self,
        tools: list | None = None,
        memory: Any | None = None,
        max_iterations: int = 3,
        verbose: bool = False,
        critique_depth: str = "thorough",
    ) -> None:
        super().__init__(
            name="CriticAgent",
            description=(
                "Provides adversarial critiques to identify weaknesses, logical "
                "flaws, and gaps in plans, code, or content."
            ),
            tools=tools,
            memory=memory,
            max_iterations=max_iterations,
            verbose=verbose,
        )
        self.critique_depth = critique_depth

    def run(self, task: str, context: dict[str, Any] | None = None) -> AgentResult:
        """
        Critique the artifact in the context.

        Args:
            task: Description of the critique focus.
            context: Context containing the artifact to critique.

        Returns:
            AgentResult with critique output.
        """
        start_time = time.time()
        self.status = AgentStatus.RUNNING
        ctx = context or {}

        self._logger.info("Starting critique", task=task)

        try:
            artifact = ctx.get("artifact") or ctx.get("output") or task
            artifact_type = ctx.get("artifact_type", "general")

            critiques = self._generate_critiques(artifact, artifact_type, task)
            counterpoints = self._generate_counterpoints(artifact, task)
            improvement_areas = self._identify_improvements(critiques)

            critique_output = {
                "critiques": critiques,
                "counterpoints": counterpoints,
                "improvement_areas": improvement_areas,
                "critique_depth": self.critique_depth,
                "overall_assessment": self._summarize(critiques),
            }

            if self.memory:
                self.memory.add(
                    {"role": "critic", "content": str(critique_output), "task": task}
                )

            self.status = AgentStatus.SUCCESS
            self._logger.info(
                "Critique complete",
                critique_count=len(critiques),
            )

            return self._create_result(
                status=AgentStatus.SUCCESS,
                output=critique_output,
                start_time=start_time,
                iterations=1,
                metadata={"critique_depth": self.critique_depth},
            )

        except Exception as exc:
            self.status = AgentStatus.FAILED
            self._logger.exception("Critique failed", error=str(exc))
            return self._create_result(
                status=AgentStatus.FAILED,
                error=str(exc),
                start_time=start_time,
            )

    def _generate_critiques(
        self,
        artifact: Any,
        artifact_type: str,
        task: str,
    ) -> list[dict[str, str]]:
        """Generate adversarial critiques of the artifact."""
        critiques: list[dict[str, str]] = []
        artifact_str = str(artifact)

        if "TODO" in artifact_str or "placeholder" in artifact_str.lower():
            critiques.append(
                {
                    "type": "completeness",
                    "issue": "Artifact contains placeholders or unimplemented sections",
                    "severity": "high",
                    "recommendation": "Replace all placeholders with concrete implementations",
                }
            )

        if len(artifact_str) < 50:
            critiques.append(
                {
                    "type": "depth",
                    "issue": "Response appears too brief for the task complexity",
                    "severity": "medium",
                    "recommendation": "Provide more detailed and comprehensive response",
                }
            )

        if artifact_type == "code":
            if "error" not in artifact_str.lower() and "exception" not in artifact_str.lower():
                critiques.append(
                    {
                        "type": "robustness",
                        "issue": "No error handling detected",
                        "severity": "medium",
                        "recommendation": "Add try/except blocks for error handling",
                    }
                )

        if not critiques:
            critiques.append(
                {
                    "type": "quality",
                    "issue": "Minor improvements possible",
                    "severity": "low",
                    "recommendation": "Consider edge cases and additional testing",
                }
            )

        return critiques

    def _generate_counterpoints(self, artifact: Any, task: str) -> list[str]:
        """Generate counterpoints to challenge the artifact's approach."""
        return [
            f"Have alternative approaches to '{task}' been considered?",
            "What are the failure modes for this solution?",
            "Are there scalability concerns at higher load/volume?",
        ]

    def _identify_improvements(
        self, critiques: list[dict[str, str]]
    ) -> list[str]:
        """Prioritize improvement areas based on critiques."""
        high_priority = [c["recommendation"] for c in critiques if c.get("severity") == "high"]
        medium_priority = [
            c["recommendation"] for c in critiques if c.get("severity") == "medium"
        ]
        low_priority = [c["recommendation"] for c in critiques if c.get("severity") == "low"]
        return high_priority + medium_priority + low_priority

    def _summarize(self, critiques: list[dict[str, str]]) -> str:
        """Summarize the critique findings."""
        if not critiques:
            return "No significant issues found."
        high = sum(1 for c in critiques if c.get("severity") == "high")
        medium = sum(1 for c in critiques if c.get("severity") == "medium")
        low = sum(1 for c in critiques if c.get("severity") == "low")
        return (
            f"Found {len(critiques)} issues: "
            f"{high} high, {medium} medium, {low} low severity."
        )
