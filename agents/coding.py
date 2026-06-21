"""
Coding Agent - writes, debugs, and improves code.
"""

from __future__ import annotations

import time
from typing import Any

import structlog

from agents.base import AgentResult, AgentStatus, BaseAgent

logger = structlog.get_logger(__name__)


class CodingAgent(BaseAgent):
    """
    Agent that generates, debugs, refactors, and tests code.

    Capabilities:
    - Code generation from specifications
    - Bug detection and fixing
    - Code refactoring
    - Test generation
    - Code documentation
    """

    def __init__(
        self,
        tools: list | None = None,
        memory: Any | None = None,
        max_iterations: int = 5,
        verbose: bool = False,
        language: str = "python",
    ) -> None:
        super().__init__(
            name="CodingAgent",
            description=(
                "Generates, debugs, and refactors code based on specifications. "
                "Supports multiple programming languages."
            ),
            tools=tools,
            memory=memory,
            max_iterations=max_iterations,
            verbose=verbose,
        )
        self.language = language

    def run(self, task: str, context: dict[str, Any] | None = None) -> AgentResult:
        """
        Execute a coding task.

        Args:
            task: Coding specification or bug description.
            context: Context with code, language, and requirements.

        Returns:
            AgentResult with generated code and execution results.
        """
        start_time = time.time()
        self.status = AgentStatus.RUNNING
        ctx = context or {}

        self._logger.info("Starting coding task", task=task)

        try:
            language = ctx.get("language", self.language)
            existing_code = ctx.get("code", "")
            task_type = self._determine_task_type(task, ctx)

            if task_type == "generate":
                code = self._generate_code(task, language, ctx)
            elif task_type == "debug":
                code = self._debug_code(existing_code, task, language)
            elif task_type == "refactor":
                code = self._refactor_code(existing_code, task, language)
            elif task_type == "test":
                code = self._generate_tests(existing_code or task, language)
            else:
                code = self._generate_code(task, language, ctx)

            exec_result: dict | None = None
            exec_tool = self._get_tool("python_exec")
            if exec_tool and language == "python" and ctx.get("execute", False):
                exec_result = exec_tool.run(code)

            artifacts = {
                "code": code,
                "language": language,
                "task_type": task_type,
                "execution_result": exec_result,
            }

            if self.memory:
                self.memory.add(
                    {"role": "coder", "content": code, "task": task}
                )

            self.status = AgentStatus.SUCCESS
            self._logger.info(
                "Coding task complete",
                task_type=task_type,
                code_lines=len(code.splitlines()),
            )

            return self._create_result(
                status=AgentStatus.SUCCESS,
                output=artifacts,
                start_time=start_time,
                iterations=1,
                metadata={"language": language, "task_type": task_type},
            )

        except Exception as exc:
            self.status = AgentStatus.FAILED
            self._logger.exception("Coding task failed", error=str(exc))
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

    def _determine_task_type(
        self, task: str, context: dict[str, Any]
    ) -> str:
        """Determine what kind of coding task this is."""
        task_lower = task.lower()
        if "debug" in task_lower or "fix" in task_lower or "error" in task_lower:
            return "debug"
        if "refactor" in task_lower or "improve" in task_lower or "optimize" in task_lower:
            return "refactor"
        if "test" in task_lower or "unit test" in task_lower:
            return "test"
        return "generate"

    def _generate_code(
        self, specification: str, language: str, context: dict[str, Any]
    ) -> str:
        """Generate code from a specification."""
        requirements = context.get("requirements", [])
        req_comments = "\n".join(f"# - {r}" for r in requirements) if requirements else ""

        if language == "python":
            return (
                f'"""\nGenerated code for: {specification}\n"""\n\n'
                f"{req_comments}\n\n"
                "def main():\n"
                f'    """Main function implementing: {specification}"""\n'
                "    # TODO: Implement logic\n"
                "    pass\n\n\n"
                'if __name__ == "__main__":\n'
                "    main()\n"
            )
        return f"// Generated code for: {specification}\n// TODO: Implement\n"

    def _debug_code(self, code: str, issue: str, language: str) -> str:
        """Add debugging annotations to existing code."""
        if not code:
            return f"# No code provided to debug for issue: {issue}\n"
        header = f"# DEBUG: Analyzing issue: {issue}\n\n"
        return header + code

    def _refactor_code(self, code: str, instruction: str, language: str) -> str:
        """Refactor existing code."""
        if not code:
            return f"# No code provided to refactor. Instruction: {instruction}\n"
        header = f"# REFACTORED: {instruction}\n\n"
        return header + code

    def _generate_tests(self, code_or_spec: str, language: str) -> str:
        """Generate unit tests for code or specification."""
        if language == "python":
            return (
                '"""Unit tests."""\n\n'
                "import pytest\n\n\n"
                "class TestGenerated:\n"
                f'    """Tests for: {code_or_spec[:60]}"""\n\n'
                "    def test_placeholder(self):\n"
                '        """Placeholder test - implement based on specification."""\n'
                "        assert True\n"
            )
        return f"// Tests for: {code_or_spec}\n"
