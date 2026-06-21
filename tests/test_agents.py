"""
Tests for agent implementations.
"""

from __future__ import annotations

import pytest

from agents.base import AgentResult, AgentStatus, BaseAgent
from agents.coding import CodingAgent
from agents.coordinator import CoordinatorAgent
from agents.critic import CriticAgent
from agents.data_analyst import DataAnalysisAgent
from agents.executor import ExecutionAgent
from agents.planner import PlannerAgent
from agents.researcher import ResearchAgent
from agents.reviewer import ReviewerAgent


class TestBaseAgent:
    """Tests for the BaseAgent abstract class."""

    def test_cannot_instantiate_directly(self):
        """BaseAgent is abstract and cannot be instantiated."""
        with pytest.raises(TypeError):
            BaseAgent(name="test", description="test")  # type: ignore[abstract]

    def test_agent_result_has_required_fields(self):
        """AgentResult must contain all required fields."""
        result = AgentResult(
            agent_id="test-id",
            agent_name="TestAgent",
            status=AgentStatus.SUCCESS,
        )
        assert result.agent_id == "test-id"
        assert result.agent_name == "TestAgent"
        assert result.status == AgentStatus.SUCCESS
        assert result.output is None
        assert result.error is None
        assert result.execution_time == 0.0
        assert result.iterations == 0

    def test_agent_status_values(self):
        """AgentStatus enum has correct values."""
        assert AgentStatus.IDLE == "idle"
        assert AgentStatus.RUNNING == "running"
        assert AgentStatus.SUCCESS == "success"
        assert AgentStatus.FAILED == "failed"
        assert AgentStatus.CANCELLED == "cancelled"


class TestPlannerAgent:
    """Tests for PlannerAgent."""

    @pytest.fixture
    def agent(self):
        return PlannerAgent()

    def test_initialization(self, agent):
        """PlannerAgent initializes with correct defaults."""
        assert agent.name == "PlannerAgent"
        assert agent.max_iterations == 5
        assert agent.status == AgentStatus.IDLE

    def test_run_returns_result(self, agent):
        """PlannerAgent.run() returns an AgentResult."""
        result = agent.run("Research Python best practices")
        assert isinstance(result, AgentResult)
        assert result.agent_name == "PlannerAgent"

    def test_run_succeeds_for_simple_task(self, agent):
        """PlannerAgent succeeds for a simple task."""
        result = agent.run("Execute a simple task")
        assert result.status == AgentStatus.SUCCESS
        assert result.output is not None

    def test_plan_has_steps(self, agent):
        """Generated plan contains steps."""
        result = agent.run("Research and analyze data")
        assert result.status == AgentStatus.SUCCESS
        plan = result.output
        assert "steps" in plan
        assert len(plan["steps"]) >= 1

    def test_plan_has_goal(self, agent):
        """Generated plan contains the original goal."""
        task = "Build a web scraper"
        result = agent.run(task)
        assert result.output["goal"] == task

    def test_research_task_creates_research_step(self, agent):
        """Research-related tasks produce a research step."""
        result = agent.run("Search for information about machine learning")
        plan = result.output
        agent_types = [s.get("agent") for s in plan["steps"]]
        assert "ResearchAgent" in agent_types

    def test_code_task_creates_coding_step(self, agent):
        """Coding tasks produce a coding step."""
        result = agent.run("Implement a sorting algorithm in Python")
        plan = result.output
        agent_types = [s.get("agent") for s in plan["steps"]]
        assert "CodingAgent" in agent_types

    def test_add_tool(self, agent):
        """Can add tools to the agent."""

        class MockTool:
            name = "mock_tool"

        tool = MockTool()
        agent.add_tool(tool)
        assert "mock_tool" in agent.get_tool_names()

    def test_repr(self, agent):
        """Agent repr is informative."""
        r = repr(agent)
        assert "PlannerAgent" in r
        assert "PlannerAgent" in r


class TestResearchAgent:
    """Tests for ResearchAgent."""

    @pytest.fixture
    def agent(self):
        return ResearchAgent()

    def test_initialization(self, agent):
        assert agent.name == "ResearchAgent"
        assert agent.max_iterations == 5

    def test_run_without_tools(self, agent):
        """Runs successfully even without tools (uses mock fallback)."""
        result = agent.run("What is machine learning?")
        assert result.status == AgentStatus.SUCCESS
        assert result.output is not None

    def test_output_contains_synthesis(self, agent):
        """Output includes a synthesis key."""
        result = agent.run("Python programming")
        assert "synthesis" in result.output

    def test_output_contains_sources(self, agent):
        """Output includes sources."""
        result = agent.run("Test query")
        assert "sources" in result.output


class TestDataAnalysisAgent:
    """Tests for DataAnalysisAgent."""

    @pytest.fixture
    def agent(self):
        return DataAnalysisAgent()

    def test_initialization(self, agent):
        assert agent.name == "DataAnalysisAgent"

    def test_run_with_no_data(self, agent):
        """Handles missing data gracefully."""
        result = agent.run("Analyze sales trends")
        assert result.status == AgentStatus.SUCCESS

    def test_run_with_data(self, agent):
        """Processes provided data correctly."""
        result = agent.run(
            "Analyze numbers",
            context={"data": {"records": [1, 2, 3, 4, 5], "columns": ["value"]}},
        )
        assert result.status == AgentStatus.SUCCESS
        assert "insights" in result.output

    def test_numerical_analysis(self, agent):
        """Computes statistics for numeric data."""
        result = agent.run(
            "Describe this dataset",
            context={"data": {"records": [10, 20, 30, 40, 50]}},
        )
        stats = result.output.get("statistics", {})
        assert stats.get("mean") == 30.0
        assert stats.get("min") == 10
        assert stats.get("max") == 50


class TestCodingAgent:
    """Tests for CodingAgent."""

    @pytest.fixture
    def agent(self):
        return CodingAgent()

    def test_initialization(self, agent):
        assert agent.name == "CodingAgent"
        assert agent.language == "python"

    def test_generate_code(self, agent):
        """Generates Python code for a specification."""
        result = agent.run("Write a hello world function")
        assert result.status == AgentStatus.SUCCESS
        assert "code" in result.output
        assert isinstance(result.output["code"], str)

    def test_debug_task_type(self, agent):
        """Identifies debug tasks."""
        result = agent.run("Fix the bug in this code")
        assert result.output["task_type"] == "debug"

    def test_refactor_task_type(self, agent):
        """Identifies refactor tasks."""
        result = agent.run("Refactor this function")
        assert result.output["task_type"] == "refactor"

    def test_test_generation_type(self, agent):
        """Identifies test generation tasks."""
        result = agent.run("Write unit tests for this module")
        assert result.output["task_type"] == "test"

    def test_generated_code_is_python(self, agent):
        """Default language is Python."""
        result = agent.run("Build a calculator function")
        assert result.output["language"] == "python"


class TestReviewerAgent:
    """Tests for ReviewerAgent."""

    @pytest.fixture
    def agent(self):
        return ReviewerAgent()

    def test_initialization(self, agent):
        assert agent.name == "ReviewerAgent"
        assert agent.pass_threshold == 0.7

    def test_run_returns_review(self, agent):
        """Returns a structured review."""
        result = agent.run("Review this code", context={"artifact": "def hello(): pass"})
        assert result.status == AgentStatus.SUCCESS
        review = result.output
        assert "score" in review
        assert "passed" in review
        assert "feedback" in review
        assert "issues" in review
        assert "suggestions" in review

    def test_score_in_valid_range(self, agent):
        """Review score is between 0 and 1."""
        result = agent.run("Review", context={"artifact": "valid content"})
        score = result.output["score"]
        assert 0.0 <= score <= 1.0

    def test_code_detection(self, agent):
        """Detects code artifacts."""
        python_code = "def foo():\n    return 42"
        result = agent.run("Review code", context={"artifact": python_code})
        assert result.metadata.get("artifact_type") == "code"

    def test_plan_detection(self, agent):
        """Detects plan artifacts."""
        plan = {"steps": [{"id": "step_1", "name": "Plan step"}], "goal": "Test"}
        result = agent.run("Review plan", context={"artifact": plan})
        assert result.metadata.get("artifact_type") == "plan"


class TestCriticAgent:
    """Tests for CriticAgent."""

    @pytest.fixture
    def agent(self):
        return CriticAgent()

    def test_initialization(self, agent):
        assert agent.name == "CriticAgent"
        assert agent.critique_depth == "thorough"

    def test_run_returns_critique(self, agent):
        """Returns structured critique output."""
        result = agent.run(
            "Critique this plan",
            context={"artifact": "TODO: implement feature"},
        )
        assert result.status == AgentStatus.SUCCESS
        output = result.output
        assert "critiques" in output
        assert "counterpoints" in output
        assert "improvement_areas" in output

    def test_detects_placeholder(self, agent):
        """Detects TODO placeholders as high-severity issue."""
        result = agent.run(
            "Critique",
            context={"artifact": "def solve(): TODO: implement this"},
        )
        critiques = result.output["critiques"]
        high_severity = [c for c in critiques if c.get("severity") == "high"]
        assert len(high_severity) >= 1


class TestExecutionAgent:
    """Tests for ExecutionAgent."""

    @pytest.fixture
    def agent(self):
        return ExecutionAgent()

    def test_initialization(self, agent):
        assert agent.name == "ExecutionAgent"

    def test_run_without_tools(self, agent):
        """Runs without tools using fallback."""
        result = agent.run("Execute basic task")
        assert result.status == AgentStatus.SUCCESS

    def test_run_returns_execution_log(self, agent):
        """Output includes execution log."""
        result = agent.run("Execute task")
        assert "execution_log" in result.output

    def test_run_with_steps_context(self, agent):
        """Executes provided steps."""
        steps = [{"id": "step_1", "tool": None, "input": "do something", "required": False}]
        result = agent.run("Execute", context={"steps": steps})
        assert result.status == AgentStatus.SUCCESS
        assert result.output["steps_executed"] >= 1


class TestCoordinatorAgent:
    """Tests for CoordinatorAgent."""

    @pytest.fixture
    def coordinator(self):
        planner = PlannerAgent()
        researcher = ResearchAgent()
        coord = CoordinatorAgent(sub_agents=[planner, researcher])
        return coord

    def test_initialization(self, coordinator):
        assert coordinator.name == "CoordinatorAgent"
        assert len(coordinator.sub_agents) == 2

    def test_register_agent(self, coordinator):
        """Can register new agents."""
        executor = ExecutionAgent()
        coordinator.register_agent(executor)
        assert "ExecutionAgent" in coordinator.sub_agents

    def test_run_coordinates_agents(self, coordinator):
        """Coordinates multiple agents for a task."""
        result = coordinator.run("Research Python and create a plan")
        assert result.status == AgentStatus.SUCCESS

    def test_output_has_summary(self, coordinator):
        """Output contains a summary."""
        result = coordinator.run("Complete a task")
        assert "summary" in result.output

    def test_unknown_agent_skipped(self):
        """Handles workflows with unregistered agents gracefully."""
        coord = CoordinatorAgent()
        result = coord.run(
            "Task",
            context={
                "workflow": [
                    {
                        "id": "step_1",
                        "agent": "NonExistentAgent",
                        "task": "do something",
                    }
                ]
            },
        )
        assert result.status == AgentStatus.SUCCESS
