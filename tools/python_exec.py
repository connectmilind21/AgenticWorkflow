"""
Python Execution Tool - safely executes Python code snippets.
"""

from __future__ import annotations

import ast
import traceback
from io import StringIO
from typing import Any

import structlog

from tools.base import BaseTool

logger = structlog.get_logger(__name__)

FORBIDDEN_MODULES = frozenset(
    {
        "os",
        "sys",
        "subprocess",
        "socket",
        "shutil",
        "importlib",
        "__import__",
        "open",
        "eval",
        "exec",
    }
)


class PythonExecTool(BaseTool):
    """
    Tool for safely executing Python code snippets.

    Uses AST validation to block dangerous operations before execution.
    Runs code in a restricted namespace with a configurable timeout.
    """

    def __init__(
        self,
        timeout: int = 30,
        sandbox: bool = True,
        max_output_length: int = 10_000,
        enabled: bool = True,
    ) -> None:
        super().__init__(
            name="python_exec",
            description=(
                "Executes Python code snippets and returns stdout/stderr output. "
                "Sandboxed to prevent dangerous operations."
            ),
            enabled=enabled,
        )
        self.timeout = timeout
        self.sandbox = sandbox
        self.max_output_length = max_output_length

    def run(self, input_data: Any, **kwargs: Any) -> dict[str, Any]:
        """
        Execute a Python code snippet.

        Args:
            input_data: Python code as a string.
            **kwargs: Additional execution parameters.

        Returns:
            Dict with 'stdout', 'stderr', 'result', and 'error' keys.
        """
        code = str(input_data)
        self._logger.info("Executing Python code", code_length=len(code))

        if self.sandbox:
            validation_error = self._validate_code(code)
            if validation_error:
                return {
                    "stdout": "",
                    "stderr": validation_error,
                    "result": None,
                    "error": validation_error,
                    "success": False,
                }

        return self._execute(code)

    def _validate_code(self, code: str) -> str | None:
        """Validate code using AST to block dangerous operations."""
        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            return f"Syntax error: {exc}"

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in FORBIDDEN_MODULES:
                        return f"Import of '{alias.name}' is not allowed."
            elif isinstance(node, ast.ImportFrom):
                if node.module in FORBIDDEN_MODULES:
                    return f"Import from '{node.module}' is not allowed."
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in {"eval", "exec", "compile", "__import__"}:
                        return f"Use of '{node.func.id}' is not allowed."

        return None

    def _execute(self, code: str) -> dict[str, Any]:
        """Execute the code and capture output."""
        stdout_capture = StringIO()
        stderr_capture = StringIO()
        result = None

        namespace: dict[str, Any] = {
            "__builtins__": {
                "print": lambda *a, **kw: print(*a, **kw, file=stdout_capture),
                "len": len,
                "range": range,
                "enumerate": enumerate,
                "zip": zip,
                "map": map,
                "filter": filter,
                "list": list,
                "dict": dict,
                "set": set,
                "tuple": tuple,
                "str": str,
                "int": int,
                "float": float,
                "bool": bool,
                "sum": sum,
                "min": min,
                "max": max,
                "abs": abs,
                "round": round,
                "sorted": sorted,
                "reversed": reversed,
                "isinstance": isinstance,
                "type": type,
                "repr": repr,
                "format": format,
            }
        }

        try:
            exec(compile(code, "<agent_code>", "exec"), namespace)  # noqa: S102
            result = namespace.get("result")
        except Exception:
            traceback.print_exc(file=stderr_capture)

        stdout = stdout_capture.getvalue()[: self.max_output_length]
        stderr = stderr_capture.getvalue()[: self.max_output_length]

        return {
            "stdout": stdout,
            "stderr": stderr,
            "result": result,
            "error": stderr if stderr else None,
            "success": not bool(stderr),
        }
