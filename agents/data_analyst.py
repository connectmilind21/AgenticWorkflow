"""
Data Analysis Agent - analyzes data and generates insights.
"""

from __future__ import annotations

import time
from typing import Any

import structlog

from agents.base import AgentResult, AgentStatus, BaseAgent

logger = structlog.get_logger(__name__)


class DataAnalysisAgent(BaseAgent):
    """
    Agent that performs data analysis, statistical modeling, and visualization.

    Capabilities:
    - Statistical analysis
    - Trend identification
    - Anomaly detection
    - Data visualization
    - Report generation
    """

    def __init__(
        self,
        tools: list | None = None,
        memory: Any | None = None,
        max_iterations: int = 5,
        verbose: bool = False,
    ) -> None:
        super().__init__(
            name="DataAnalysisAgent",
            description=(
                "Performs statistical analysis, identifies trends and patterns, "
                "and generates actionable insights from structured data."
            ),
            tools=tools,
            memory=memory,
            max_iterations=max_iterations,
            verbose=verbose,
        )

    def run(self, task: str, context: dict[str, Any] | None = None) -> AgentResult:
        """
        Analyze data based on the given task description.

        Args:
            task: Analysis task or question.
            context: Context including data, parameters, and format requirements.

        Returns:
            AgentResult with analysis findings and insights.
        """
        start_time = time.time()
        self.status = AgentStatus.RUNNING
        ctx = context or {}

        self._logger.info("Starting data analysis", task=task)

        try:
            data = ctx.get("data")
            analysis_type = ctx.get("analysis_type", "general")

            if data is None:
                data = self._collect_data(task, ctx)

            results = self._analyze(data, task, analysis_type)
            insights = self._generate_insights(results, task)

            exec_tool = self._get_tool("python_exec")
            code_results: dict | None = None
            if exec_tool and ctx.get("run_code", False):
                code = self._generate_analysis_code(data, analysis_type)
                code_results = exec_tool.run(code)

            if self.memory:
                self.memory.add(
                    {"role": "analyst", "content": str(insights), "task": task}
                )

            self.status = AgentStatus.SUCCESS
            self._logger.info("Data analysis complete", insights=len(insights))

            return self._create_result(
                status=AgentStatus.SUCCESS,
                output={
                    "insights": insights,
                    "statistics": results,
                    "code_results": code_results,
                    "task": task,
                },
                start_time=start_time,
                iterations=1,
                metadata={"analysis_type": analysis_type},
            )

        except Exception as exc:
            self.status = AgentStatus.FAILED
            self._logger.exception("Data analysis failed", error=str(exc))
            return self._create_result(
                status=AgentStatus.FAILED,
                error=str(exc),
                start_time=start_time,
            )

    def _get_tool(self, tool_name: str) -> Any | None:
        """Retrieve a tool by name."""
        for tool in self.tools:
            if getattr(tool, "name", None) == tool_name:
                return tool
        return None

    def _collect_data(
        self, task: str, context: dict[str, Any]
    ) -> dict[str, Any]:
        """Collect data when none is provided."""
        return {
            "description": f"Dataset for: {task}",
            "records": [],
            "columns": [],
        }

    def _analyze(
        self,
        data: Any,
        task: str,
        analysis_type: str,
    ) -> dict[str, Any]:
        """Perform core analysis on the data."""
        if isinstance(data, dict):
            records = data.get("records", [])
        elif isinstance(data, list):
            records = data
        else:
            records = []

        stats: dict[str, Any] = {
            "record_count": len(records),
            "analysis_type": analysis_type,
            "task": task,
        }

        if records and isinstance(records[0], (int, float)):
            nums = [r for r in records if isinstance(r, (int, float))]
            if nums:
                stats["min"] = min(nums)
                stats["max"] = max(nums)
                stats["mean"] = sum(nums) / len(nums)
                stats["count"] = len(nums)

        return stats

    def _generate_insights(
        self,
        results: dict[str, Any],
        task: str,
    ) -> list[str]:
        """Convert analysis results into human-readable insights."""
        insights: list[str] = []

        insights.append(
            f"Analysis of '{task}' processed {results.get('record_count', 0)} records."
        )

        if "mean" in results:
            insights.append(
                f"Average value: {results['mean']:.2f} "
                f"(range: {results['min']} - {results['max']})"
            )

        return insights

    def _generate_analysis_code(self, data: Any, analysis_type: str) -> str:
        """Generate Python code to perform the analysis."""
        return (
            "import json\n"
            f"data = {data!r}\n"
            "print(f'Analysis type: {analysis_type}')\n"
            "print(f'Data: {{data}}')\n"
        )
