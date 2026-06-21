"""
Research Agent - gathers and synthesizes information from multiple sources.
"""

from __future__ import annotations

import time
from typing import Any

import structlog

from agents.base import AgentResult, AgentStatus, BaseAgent

logger = structlog.get_logger(__name__)


class ResearchAgent(BaseAgent):
    """
    Agent that performs web research, information gathering, and synthesis.

    Capabilities:
    - Multi-source web search
    - Content summarization
    - Fact extraction
    - Source citation
    """

    def __init__(
        self,
        tools: list | None = None,
        memory: Any | None = None,
        max_iterations: int = 5,
        verbose: bool = False,
    ) -> None:
        super().__init__(
            name="ResearchAgent",
            description=(
                "Performs comprehensive research by searching multiple sources, "
                "extracting relevant information, and synthesizing findings."
            ),
            tools=tools,
            memory=memory,
            max_iterations=max_iterations,
            verbose=verbose,
        )

    def run(self, task: str, context: dict[str, Any] | None = None) -> AgentResult:
        """
        Conduct research on the given topic or question.

        Args:
            task: Research query or topic.
            context: Optional context with search parameters.

        Returns:
            AgentResult with research findings.
        """
        start_time = time.time()
        self.status = AgentStatus.RUNNING

        self._logger.info("Starting research", task=task)

        try:
            findings: list[dict[str, Any]] = []
            iterations = 0

            search_tool = self._get_tool("web_search")

            if search_tool:
                for i in range(min(self.max_iterations, 3)):
                    iterations += 1
                    query = self._refine_query(task, i, findings)
                    result = search_tool.run(query)
                    if result:
                        findings.extend(
                            result if isinstance(result, list) else [result]
                        )
                    if self._is_sufficient(findings, task):
                        break
            else:
                iterations = 1
                findings = [
                    {
                        "source": "mock",
                        "content": f"Research findings for: {task}",
                        "relevance": 1.0,
                    }
                ]

            synthesis = self._synthesize(findings, task)

            if self.memory:
                self.memory.add(
                    {"role": "researcher", "content": synthesis, "task": task}
                )

            self.status = AgentStatus.SUCCESS
            self._logger.info(
                "Research complete",
                sources=len(findings),
                iterations=iterations,
            )

            return self._create_result(
                status=AgentStatus.SUCCESS,
                output={
                    "synthesis": synthesis,
                    "sources": findings,
                    "query": task,
                    "source_count": len(findings),
                },
                start_time=start_time,
                iterations=iterations,
                metadata={"task": task},
            )

        except Exception as exc:
            self.status = AgentStatus.FAILED
            self._logger.exception("Research failed", error=str(exc))
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

    def _refine_query(
        self, original: str, iteration: int, previous_findings: list
    ) -> str:
        """Refine search query based on previous results."""
        if iteration == 0:
            return original
        if iteration == 1:
            return f"{original} latest developments"
        return f"{original} detailed analysis"

    def _is_sufficient(self, findings: list, task: str) -> bool:
        """Determine if gathered findings are sufficient."""
        return len(findings) >= 3

    def _synthesize(self, findings: list[dict[str, Any]], task: str) -> str:
        """Synthesize findings into a coherent summary."""
        if not findings:
            return f"No relevant information found for: {task}"

        contents = [
            f.get("content", f.get("snippet", str(f)))
            for f in findings
            if f
        ]
        combined = " ".join(str(c) for c in contents[:5])

        return (
            f"Research Summary for '{task}':\n\n"
            f"Based on {len(findings)} sources:\n{combined[:2000]}"
        )
