"""
Tests for tool implementations.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from tools.base import BaseTool, ToolResult, ToolStatus
from tools.database import DatabaseTool
from tools.file_operations import FileOperationsTool
from tools.python_exec import PythonExecTool
from tools.shell import ShellTool
from tools.web_search import WebSearchTool


class TestBaseTool:
    """Tests for BaseTool."""

    def test_cannot_instantiate_directly(self):
        """BaseTool is abstract."""
        with pytest.raises(TypeError):
            BaseTool(name="test", description="test")  # type: ignore[abstract]

    def test_tool_result_model(self):
        """ToolResult model works correctly."""
        result = ToolResult(
            tool_name="test",
            status=ToolStatus.SUCCESS,
            output="hello",
        )
        assert result.tool_name == "test"
        assert result.status == ToolStatus.SUCCESS
        assert result.output == "hello"


class TestWebSearchTool:
    """Tests for WebSearchTool."""

    @pytest.fixture
    def tool(self):
        return WebSearchTool(provider="mock")

    def test_initialization(self, tool):
        assert tool.name == "web_search"
        assert tool.enabled is True

    def test_mock_search_returns_results(self, tool):
        """Mock search returns expected number of results."""
        results = tool.run("Python programming")
        assert isinstance(results, list)
        assert len(results) > 0

    def test_results_have_required_keys(self, tool):
        """Each result has title, snippet, url, relevance."""
        results = tool.run("test query")
        for result in results:
            assert "title" in result
            assert "snippet" in result
            assert "url" in result
            assert "relevance" in result

    def test_max_results_respected(self, tool):
        """Respects max_results parameter."""
        results = tool.run("query", max_results=2)
        assert len(results) <= 2

    def test_disabled_tool_returns_disabled_result(self):
        """Disabled tools return ToolStatus.DISABLED."""
        tool = WebSearchTool(enabled=False)
        result = tool(query="test")
        assert isinstance(result, ToolResult)
        assert result.status == ToolStatus.DISABLED

    def test_repr(self, tool):
        assert "web_search" in repr(tool)


class TestFileOperationsTool:
    """Tests for FileOperationsTool."""

    @pytest.fixture
    def tmp_dir(self):
        with tempfile.TemporaryDirectory() as d:
            yield d

    @pytest.fixture
    def tool(self, tmp_dir):
        return FileOperationsTool(base_dir=tmp_dir)

    def test_initialization(self, tool):
        assert tool.name == "file_operations"

    def test_write_and_read_file(self, tool):
        """Can write and then read a file."""
        tool.run({"operation": "write", "path": "test.txt", "content": "hello world"})
        content = tool.run({"operation": "read", "path": "test.txt"})
        assert content == "hello world"

    def test_read_string_input(self, tool):
        """String input is treated as a read path."""
        tool.run({"operation": "write", "path": "data.txt", "content": "test data"})
        content = tool.run("data.txt")
        assert content == "test data"

    def test_list_directory(self, tool, tmp_dir):
        """Lists files in directory."""
        Path(tmp_dir, "file1.txt").write_text("content1")
        Path(tmp_dir, "file2.md").write_text("content2")
        entries = tool.run({"operation": "list", "path": "."})
        names = [e["name"] for e in entries]
        assert "file1.txt" in names
        assert "file2.md" in names

    def test_delete_file(self, tool, tmp_dir):
        """Can delete a file."""
        Path(tmp_dir, "delete_me.txt").write_text("bye")
        result = tool.run({"operation": "delete", "path": "delete_me.txt"})
        assert result is True
        assert not Path(tmp_dir, "delete_me.txt").exists()

    def test_search_files(self, tool, tmp_dir):
        """Searches file contents."""
        Path(tmp_dir, "a.txt").write_text("contains keyword here")
        Path(tmp_dir, "b.txt").write_text("no match here")
        results = tool.run({"operation": "search", "query": "keyword", "path": "."})
        paths = [r["path"] for r in results]
        assert any("a.txt" in p for p in paths)

    def test_disallows_path_traversal(self, tool):
        """Blocks path traversal attempts."""
        with pytest.raises(PermissionError):
            tool.run({"operation": "read", "path": "../../etc/passwd"})

    def test_disallows_unknown_extension(self, tool):
        """Blocks files with disallowed extensions."""
        with pytest.raises(ValueError):
            tool.run({"operation": "write", "path": "script.sh", "content": "rm -rf /"})

    def test_missing_file_raises(self, tool):
        """Reading non-existent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            tool.run("nonexistent.txt")

    def test_unknown_operation_raises(self, tool):
        """Unknown operation raises ValueError."""
        with pytest.raises(ValueError):
            tool.run({"operation": "fly", "path": "test.txt"})


class TestDatabaseTool:
    """Tests for DatabaseTool."""

    @pytest.fixture
    def tool(self):
        return DatabaseTool()

    def test_initialization(self, tool):
        assert tool.name == "database"
        assert tool.allow_writes is False

    def test_select_query_returns_mock(self, tool):
        """SELECT query returns mock data when no DB configured."""
        results = tool.run("SELECT * FROM users LIMIT 10")
        assert isinstance(results, list)
        assert len(results) > 0

    def test_dict_input(self, tool):
        """Accepts dict input with query key."""
        results = tool.run({"query": "SELECT 1"})
        assert isinstance(results, list)

    def test_blocks_write_operations(self, tool):
        """Blocks INSERT/UPDATE/DELETE by default."""
        with pytest.raises(PermissionError):
            tool.run("INSERT INTO users VALUES (1, 'alice')")

    def test_allows_writes_when_enabled(self):
        """Allows writes when allow_writes=True."""
        tool = DatabaseTool(allow_writes=True)
        # No real DB, so will use mock
        result = tool.run("INSERT INTO test VALUES (1)")
        assert isinstance(result, list)

    def test_blocks_dangerous_sql(self, tool):
        """Blocks SQL injection patterns."""
        with pytest.raises(ValueError):
            tool.run("SELECT * FROM users -- comment")


class TestPythonExecTool:
    """Tests for PythonExecTool."""

    @pytest.fixture
    def tool(self):
        return PythonExecTool(sandbox=True)

    def test_initialization(self, tool):
        assert tool.name == "python_exec"
        assert tool.sandbox is True

    def test_basic_execution(self, tool):
        """Executes simple Python code."""
        result = tool.run("result = 1 + 1")
        assert result["success"] is True
        assert result["result"] == 2

    def test_print_captured(self, tool):
        """Captures print output."""
        result = tool.run("print('hello world')")
        assert "hello world" in result["stdout"]

    def test_blocks_os_import(self, tool):
        """Blocks import of os module."""
        result = tool.run("import os; os.listdir('.')")
        assert result["success"] is False
        assert "not allowed" in result["error"].lower()

    def test_blocks_eval(self, tool):
        """Blocks eval() calls."""
        result = tool.run("eval('1+1')")
        assert result["success"] is False

    def test_syntax_error_handled(self, tool):
        """Syntax errors are caught and returned."""
        result = tool.run("def broken syntax:")
        assert result["success"] is False
        assert "syntax" in result["error"].lower()

    def test_sandbox_disabled(self):
        """Without sandbox, os import is allowed."""
        tool = PythonExecTool(sandbox=False)
        result = tool.run("result = 2 + 2")
        assert result["result"] == 4

    def test_arithmetic(self, tool):
        """Basic arithmetic works."""
        result = tool.run("result = sum(range(1, 6))")
        assert result["result"] == 15


class TestShellTool:
    """Tests for ShellTool."""

    @pytest.fixture
    def tool(self):
        return ShellTool(enabled=True, allowed_commands=["echo", "pwd"])

    def test_initialization(self):
        """ShellTool is disabled by default."""
        tool = ShellTool()
        assert tool.enabled is False

    def test_echo_command(self, tool):
        """Executes allowed echo command."""
        result = tool.run(["echo", "hello"])
        assert result["success"] is True
        assert "hello" in result["stdout"]

    def test_blocks_disallowed_command(self, tool):
        """Blocks commands not in allowlist."""
        with pytest.raises(PermissionError):
            tool.run(["rm", "-rf", "/"])

    def test_empty_command_raises(self, tool):
        """Empty command raises ValueError."""
        with pytest.raises(ValueError):
            tool.run("")

    def test_string_input(self, tool):
        """Accepts string input."""
        result = tool.run("echo test")
        assert result["success"] is True

    def test_command_not_found(self, tool):
        """Non-existent command returns failure."""
        tool.allowed_commands.add("totally_fake_command_xyz")
        result = tool.run("totally_fake_command_xyz")
        assert result["success"] is False
