"""
Tests for workflow implementations.
"""

from __future__ import annotations

import pytest

from agents.planner import PlannerAgent
from agents.researcher import ResearchAgent
from agents.reviewer import ReviewerAgent
from workflows.base import WorkflowResult, WorkflowStatus, WorkflowStep
from workflows.conditional import ConditionalWorkflow
from workflows.multi_agent import MultiAgentWorkflow
from workflows.parallel import ParallelWorkflow
from workflows.sequential import SequentialWorkflow


def make_step(step_id: str, agent_name: str = None, task: str = "test task") -> WorkflowStep:
    """Create a simple workflow step for testing."""
    return WorkflowStep(
        id=step_id,
        name=f"Step {step_id}",
        agent_name=agent_name,
        task=task,
    )


class TestWorkflowStep:
    """Tests for WorkflowStep model."""

    def test_creation(self):
        step = WorkflowStep(id="s1", name="Step 1")
        assert step.id == "s1"
        assert step.required is True
        assert step.max_retries == 2
        assert step.depends_on == []

    def test_with_dependencies(self):
        step = WorkflowStep(id="s2", name="Step 2", depends_on=["s1"])
        assert "s1" in step.depends_on


class TestWorkflowResult:
    """Tests for WorkflowResult model."""

    def test_creation(self):
        result = WorkflowResult(
            workflow_id="wf-1",
            workflow_name="test",
            status=WorkflowStatus.SUCCESS,
        )
        assert result.workflow_id == "wf-1"
        assert result.status == WorkflowStatus.SUCCESS
        assert result.steps_total == 0
        assert result.errors == []


class TestSequentialWorkflow:
    """Tests for SequentialWorkflow."""

    @pytest.fixture
    def workflow(self):
        wf = SequentialWorkflow(name="test_workflow")
        wf.register_agent(PlannerAgent())
        wf.register_agent(ResearchAgent())
        return wf

    def test_initialization(self, workflow):
        assert workflow.name == "test_workflow"
        assert workflow.status == WorkflowStatus.PENDING

    def test_execute_empty_workflow(self, workflow):
        """Empty workflow completes successfully."""
        result = workflow.execute()
        assert result.status == WorkflowStatus.SUCCESS
        assert result.steps_total == 0

    def test_execute_with_steps(self, workflow):
        """Executes steps in order."""
        workflow.add_step(make_step("s1", "PlannerAgent", "Plan something"))
        workflow.add_step(make_step("s2", "ResearchAgent", "Research something"))
        result = workflow.execute(context={"task": "test task"})
        assert result.status in (WorkflowStatus.SUCCESS, WorkflowStatus.PARTIAL)
        assert result.steps_total == 2

    def test_output_passed_between_steps(self, workflow):
        """Step outputs available in context for subsequent steps."""
        workflow.add_step(make_step("s1", "PlannerAgent", "Plan a research project"))
        result = workflow.execute(context={"task": "test"})
        assert "s1" in result.outputs

    def test_stop_on_failure(self):
        """Stops when required step fails and stop_on_failure=True."""
        wf = SequentialWorkflow(name="fail_test", stop_on_failure=True)

        failing_step = WorkflowStep(
            id="fail",
            name="Fail",
            agent_name="NonExistentAgent",
            task="fail",
            required=True,
            max_retries=0,
        )
        wf.add_step(failing_step)

        result = wf.execute()
        assert result.status in (WorkflowStatus.FAILED, WorkflowStatus.PARTIAL)

    def test_continue_on_optional_failure(self):
        """Continues when optional step fails and stop_on_failure=True."""
        wf = SequentialWorkflow(name="optional_test", stop_on_failure=True)
        planner = PlannerAgent()
        wf.register_agent(planner)

        optional_fail = WorkflowStep(
            id="optional",
            name="Optional",
            agent_name="GhostAgent",
            task="fail",
            required=False,
            max_retries=0,
        )
        good_step = make_step("good", "PlannerAgent", "Complete this task")
        wf.add_step(optional_fail)
        wf.add_step(good_step)

        result = wf.execute(context={"task": "test"})
        assert result.steps_succeeded >= 1

    def test_add_hook(self, workflow):
        """Lifecycle hooks are called."""
        called = []
        workflow.add_hook("before_step", lambda step, context: called.append("before"))
        workflow.add_step(make_step("s1", "PlannerAgent", "test"))
        workflow.execute(context={"task": "test"})
        assert "before" in called

    def test_repr(self, workflow):
        r = repr(workflow)
        assert "SequentialWorkflow" in r
        assert "test_workflow" in r


class TestParallelWorkflow:
    """Tests for ParallelWorkflow."""

    @pytest.fixture
    def workflow(self):
        wf = ParallelWorkflow(name="parallel_test", max_workers=2)
        wf.register_agent(PlannerAgent())
        wf.register_agent(ResearchAgent())
        return wf

    def test_initialization(self, workflow):
        assert workflow.name == "parallel_test"
        assert workflow.max_workers == 2

    def test_execute_no_steps(self, workflow):
        """Empty workflow completes successfully."""
        result = workflow.execute()
        assert result.status == WorkflowStatus.SUCCESS

    def test_execute_independent_steps(self, workflow):
        """Independent steps run in parallel."""
        workflow.add_step(make_step("s1", "PlannerAgent", "Plan A"))
        workflow.add_step(make_step("s2", "ResearchAgent", "Research B"))
        result = workflow.execute(context={"task": "test"})
        assert result.steps_total == 2
        assert result.status in (WorkflowStatus.SUCCESS, WorkflowStatus.PARTIAL)

    def test_resolve_batches_sequential_deps(self):
        """Steps with dependencies are batched sequentially."""
        wf = ParallelWorkflow(name="dep_test")
        steps = [
            WorkflowStep(id="a", name="A", depends_on=[]),
            WorkflowStep(id="b", name="B", depends_on=["a"]),
            WorkflowStep(id="c", name="C", depends_on=["b"]),
        ]
        batches = wf._resolve_batches(steps)
        assert len(batches) == 3
        assert batches[0][0].id == "a"
        assert batches[1][0].id == "b"
        assert batches[2][0].id == "c"

    def test_resolve_batches_independent(self):
        """Steps without dependencies run in single batch."""
        wf = ParallelWorkflow(name="indep_test")
        steps = [
            WorkflowStep(id="a", name="A"),
            WorkflowStep(id="b", name="B"),
            WorkflowStep(id="c", name="C"),
        ]
        batches = wf._resolve_batches(steps)
        assert len(batches) == 1
        assert len(batches[0]) == 3


class TestConditionalWorkflow:
    """Tests for ConditionalWorkflow."""

    @pytest.fixture
    def workflow(self):
        wf = ConditionalWorkflow(name="conditional_test")
        wf.register_agent(PlannerAgent())
        wf.register_agent(ResearchAgent())
        return wf

    def test_initialization(self, workflow):
        assert workflow.name == "conditional_test"

    def test_true_branch_executed(self, workflow):
        """Executes branch when condition is True."""
        branch_steps = [make_step("branch_s1", "PlannerAgent", "plan")]
        workflow.add_branch(
            condition=lambda ctx: ctx.get("use_research", False) is False,
            steps=branch_steps,
            name="no_research",
        )

        result = workflow.execute(context={"task": "test", "use_research": False})
        assert result.metadata.get("executed_branch") == "no_research"

    def test_default_branch_when_no_condition_matches(self, workflow):
        """Executes default branch when no condition matches."""
        default_steps = [make_step("default_s1", "PlannerAgent", "default task")]
        workflow.add_branch(
            condition=lambda ctx: False,  # Never matches
            steps=[],
            name="never",
        )
        workflow.set_default(default_steps)

        result = workflow.execute(context={"task": "test"})
        assert result.metadata.get("executed_branch") is None
        assert result.steps_succeeded >= 1

    def test_condition_exception_skips_branch(self, workflow):
        """Branch with raising condition is skipped."""
        def bad_condition(ctx):
            raise RuntimeError("condition error")

        workflow.add_branch(condition=bad_condition, steps=[], name="bad")
        result = workflow.execute(context={"task": "test"})
        assert result.status in (WorkflowStatus.SUCCESS, WorkflowStatus.PARTIAL)


class TestMultiAgentWorkflow:
    """Tests for MultiAgentWorkflow."""

    @pytest.fixture
    def workflow(self):
        wf = MultiAgentWorkflow(name="multi_test", collaboration_mode="pipeline")
        wf.register_agent(PlannerAgent())
        wf.register_agent(ResearchAgent())
        return wf

    def test_initialization(self, workflow):
        assert workflow.name == "multi_test"
        assert workflow.collaboration_mode == "pipeline"

    def test_pipeline_mode(self, workflow):
        """Pipeline mode executes agents sequentially."""
        result = workflow.execute(context={"task": "Research and plan AI trends"})
        assert result.status in (WorkflowStatus.SUCCESS, WorkflowStatus.PARTIAL)
        assert "PlannerAgent" in result.outputs or "ResearchAgent" in result.outputs

    def test_debate_mode(self):
        """Debate mode runs multiple rounds."""
        wf = MultiAgentWorkflow(
            name="debate_test",
            collaboration_mode="debate",
            max_rounds=2,
        )
        wf.register_agent(PlannerAgent())
        wf.register_agent(ReviewerAgent())
        result = wf.execute(context={"task": "Plan a project"})
        assert result.status in (WorkflowStatus.SUCCESS, WorkflowStatus.PARTIAL)
        assert "round_1" in result.outputs
        assert "round_2" in result.outputs

    def test_voting_mode(self):
        """Voting mode runs all agents and selects winner."""
        wf = MultiAgentWorkflow(
            name="voting_test",
            collaboration_mode="voting",
        )
        wf.register_agent(PlannerAgent())
        wf.register_agent(ResearchAgent())
        result = wf.execute(context={"task": "Solve a problem"})
        assert result.status in (WorkflowStatus.SUCCESS, WorkflowStatus.PARTIAL)
        assert "winner" in result.outputs

    def test_unknown_mode_defaults_to_pipeline(self):
        """Unknown collaboration mode falls back to pipeline."""
        wf = MultiAgentWorkflow(
            name="unknown_mode",
            collaboration_mode="telepathy",
        )
        wf.register_agent(PlannerAgent())
        result = wf.execute(context={"task": "test"})
        assert result.status in (WorkflowStatus.SUCCESS, WorkflowStatus.PARTIAL)
