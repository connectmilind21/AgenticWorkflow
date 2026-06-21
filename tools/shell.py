"""
Shell Command Tool - executes shell commands in a restricted environment.
"""

from __future__ import annotations

import shlex
import subprocess
from typing import Any

import structlog

from tools.base import BaseTool

logger = structlog.get_logger(__name__)

DEFAULT_ALLOWED_COMMANDS: list[str] = ["echo", "ls", "cat", "pwd", "date", "wc"]


class ShellTool(BaseTool):
    """
    Tool for executing shell commands.

    Disabled by default for security. When enabled, only commands in the
    allowlist may be executed. Commands are never passed to a shell
    interpreter — they are executed directly to prevent injection.
    """

    def __init__(
        self,
        allowed_commands: list[str] | None = None,
        timeout: int = 30,
        enabled: bool = False,
    ) -> None:
        super().__init__(
            name="shell",
            description=(
                "Executes allowed shell commands. Disabled by default. "
                "Only whitelisted commands can be executed."
            ),
            enabled=enabled,
        )
        self.allowed_commands = set(allowed_commands or DEFAULT_ALLOWED_COMMANDS)
        self.timeout = timeout

    def run(self, input_data: Any, **kwargs: Any) -> dict[str, Any]:
        """
        Execute a shell command.

        Args:
            input_data: Command string or list of command arguments.
            **kwargs: Additional parameters.

        Returns:
            Dict with 'stdout', 'stderr', 'returncode', and 'success' keys.
        """
        if isinstance(input_data, str):
            args = shlex.split(input_data)
        elif isinstance(input_data, list):
            args = [str(a) for a in input_data]
        else:
            raise TypeError(f"Unexpected input type: {type(input_data)}")

        if not args:
            raise ValueError("No command provided.")

        command = args[0]
        if command not in self.allowed_commands:
            raise PermissionError(
                f"Command '{command}' is not in the allowlist: {sorted(self.allowed_commands)}"
            )

        self._logger.info("Executing shell command", command=command, args=args[1:])

        try:
            proc = subprocess.run(  # noqa: S603
                args,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=False,
            )
            return {
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "returncode": proc.returncode,
                "success": proc.returncode == 0,
            }
        except subprocess.TimeoutExpired:
            return {
                "stdout": "",
                "stderr": f"Command timed out after {self.timeout}s",
                "returncode": -1,
                "success": False,
            }
        except FileNotFoundError:
            return {
                "stdout": "",
                "stderr": f"Command not found: {command}",
                "returncode": -1,
                "success": False,
            }
