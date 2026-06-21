"""
Reviewer Agent - reviews outputs and provides structured feedback.
"""

from __future__ import annotations

import time
from typing import Any

import structlog

from agents.base import AgentResult, AgentStatus, BaseAgent

logger = structlog.get_logger(__name__)


class ReviewResult(dict):
    """Structured review result."""

    @classmethod
    def create(
        cls,
        score: float,
        passed: bool,
        feedback: list[str],
        issues: list[dict[str, str]],
        suggestions: list[str],
    ) -> ReviewResult:
        instance = cls()
        instance["score"] = score
        instance["passed"] = passed
        instance["feedback"] = feedback
        instance["issues"] = issues
        instance["suggestions"] = suggestions
        return instance


class ReviewerAgent(BaseAgent):
    """
    Agent that reviews code, content, or plans and provides structured feedback.

    Capabilities:
    - Code review
    - Plan review
    - Content quality assessment
    - Compliance checking
    - Improvement suggestions
    """

    def __init__(
        self,
        tools: list | None = None,
        memory: Any | None = None,
        max_iterations: int = 3,
        verbose: bool = False,
        pass_threshold: float = 0.7,
    ) -> None:
        super().__init__(
            name="ReviewerAgent",
            description=(
                "Reviews artifacts (code, plans, content) and provides structured "
                "feedback with scores, issues, and improvement suggestions."
            ),
            tools=tools,
            memory=memory,
            max_iterations=max_iterations,
            verbose=verbose,
        )
        self.pass_threshold = pass_threshold

    def run(self, task: str, context: dict[str, Any] | None = None) -> AgentResult:
        """
        Review the artifact described in the task.

        Args:
            task: Description of what to review.
            context: Context containing the artifact to review.

        Returns:
            AgentResult with ReviewResult as output.
        """
        start_time = time.time()
        self.status = AgentStatus.RUNNING
        ctx = context or {}

        self._logger.info("Starting review", task=task)

        try:
            artifact = ctx.get("artifact") or ctx.get("code") or ctx.get("content") or task
            artifact_type = ctx.get("artifact_type", self._detect_type(artifact))
            criteria = ctx.get("criteria", self._default_criteria(artifact_type))

            review = self._review(artifact, artifact_type, criteria, task)

            if self.memory:
                self.memory.add(
                    {
                        "role": "reviewer",
                        "content": str(review),
                        "task": task,
                        "passed": review["passed"],
                    }
                )

            self.status = AgentStatus.SUCCESS
            self._logger.info(
                "Review complete",
                score=review["score"],
                passed=review["passed"],
                issue_count=len(review["issues"]),
            )

            return self._create_result(
                status=AgentStatus.SUCCESS,
                output=review,
                start_time=start_time,
                iterations=1,
                metadata={
                    "artifact_type": artifact_type,
                    "passed": review["passed"],
                    "score": review["score"],
                },
            )

        except Exception as exc:
            self.status = AgentStatus.FAILED
            self._logger.exception("Review failed", error=str(exc))
            return self._create_result(
                status=AgentStatus.FAILED,
                error=str(exc),
                start_time=start_time,
            )

    def _detect_type(self, artifact: Any) -> str:
        """Detect the type of artifact being reviewed."""
        if isinstance(artifact, str):
            text = artifact.lower()
            if any(kw in text for kw in ["def ", "class ", "import ", "return "]):
                return "code"
            if any(kw in text for kw in ["step", "plan", "goal", "objective"]):
                return "plan"
        if isinstance(artifact, dict):
            if "steps" in artifact:
                return "plan"
            if "code" in artifact:
                return "code"
        return "content"

    def _default_criteria(self, artifact_type: str) -> list[str]:
        """Return default review criteria for an artifact type."""
        criteria_map = {
            "code": [
                "correctness",
                "readability",
                "performance",
                "security",
                "test_coverage",
            ],
            "plan": [
                "completeness",
                "feasibility",
                "clarity",
                "dependencies",
            ],
            "content": [
                "accuracy",
                "clarity",
                "completeness",
                "relevance",
            ],
        }
        return criteria_map.get(artifact_type, criteria_map["content"])

    def _review(
        self,
        artifact: Any,
        artifact_type: str,
        criteria: list[str],
        task: str,
    ) -> ReviewResult:
        """Perform a structured review."""
        issues: list[dict[str, str]] = []
        feedback: list[str] = []
        criterion_scores: list[float] = []

        for criterion in criteria:
            score, issue, comment = self._evaluate_criterion(
                artifact, criterion, artifact_type
            )
            criterion_scores.append(score)
            feedback.append(f"{criterion}: {comment}")
            if issue:
                issues.append({"criterion": criterion, "issue": issue, "severity": "medium"})

        overall_score = (
            sum(criterion_scores) / len(criterion_scores) if criterion_scores else 0.5
        )
        passed = overall_score >= self.pass_threshold

        suggestions = self._generate_suggestions(issues, artifact_type)

        return ReviewResult.create(
            score=round(overall_score, 2),
            passed=passed,
            feedback=feedback,
            issues=issues,
            suggestions=suggestions,
        )

    def _evaluate_criterion(
        self,
        artifact: Any,
        criterion: str,
        artifact_type: str,
    ) -> tuple[float, str | None, str]:
        """Evaluate a single review criterion. Returns (score, issue, comment)."""
        if artifact_type == "code" and isinstance(artifact, str):
            if criterion == "correctness":
                if "TODO" in artifact or "pass" in artifact:
                    return 0.6, "Incomplete implementation detected", "Contains TODO/pass"
                return 0.9, None, "Code appears complete"
            if criterion == "readability":
                lines = artifact.splitlines()
                if len(lines) > 0 and any('"""' in line or "#" in line for line in lines):
                    return 0.9, None, "Well documented"
                return 0.7, None, "Consider adding docstrings"
            if criterion == "security":
                dangerous = ["eval(", "exec(", "subprocess", "os.system"]
                if any(d in artifact for d in dangerous):
                    return 0.4, "Potentially unsafe function usage", "Review security"
                return 0.9, None, "No obvious security issues"
        return 0.8, None, "Meets criterion"

    def _generate_suggestions(
        self, issues: list[dict], artifact_type: str
    ) -> list[str]:
        """Generate actionable improvement suggestions."""
        suggestions: list[str] = []
        for issue in issues:
            criterion = issue.get("criterion", "")
            if criterion == "correctness":
                suggestions.append("Replace placeholder code with actual implementation.")
            elif criterion == "security":
                suggestions.append(
                    "Avoid using eval/exec; use ast.literal_eval or safer alternatives."
                )
            elif criterion == "readability":
                suggestions.append("Add docstrings and inline comments for complex logic.")
        if not suggestions:
            suggestions.append(f"The {artifact_type} is well-structured. Minor polish recommended.")
        return suggestions
