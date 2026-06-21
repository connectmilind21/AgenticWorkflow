"""
Workflow API routes.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class WorkflowRunRequest(BaseModel):
    """Request model for running a workflow."""

    workflow_type: str
    task: str
    context: dict[str, Any] | None = None
    agent_types: list[str] | None = None


class WorkflowRunResponse(BaseModel):
    """Response model for workflow execution."""

    workflow_id: str
    workflow_name: str
    status: str
    steps_total: int = 0
    steps_succeeded: int = 0
    steps_failed: int = 0
    outputs: dict[str, Any] = {}
    errors: list[str] = []
    execution_time: float = 0.0


@router.get("/", summary="List available workflow types")
async def list_workflows() -> dict[str, Any]:
    """Return list of available workflow types."""
    return {
        "workflows": [
            {
                "type": "sequential",
                "description": "Execute steps one after another",
            },
            {
                "type": "parallel",
                "description": "Execute independent steps concurrently",
            },
            {
                "type": "conditional",
                "description": "Execute steps based on conditions",
            },
            {
                "type": "multi_agent",
                "description": "Coordinate multiple agents collaboratively",
            },
        ]
    }


@router.post("/run", summary="Run a workflow", response_model=WorkflowRunResponse)
async def run_workflow(request: WorkflowRunRequest) -> WorkflowRunResponse:
    """Execute a workflow with the given task and context."""
    from agents.executor import ExecutionAgent
    from agents.planner import PlannerAgent
    from agents.researcher import ResearchAgent
    from workflows.multi_agent import MultiAgentWorkflow
    from workflows.sequential import SequentialWorkflow

    workflow_classes = {
        "sequential": SequentialWorkflow,
        "multi_agent": MultiAgentWorkflow,
    }

    workflow_class = workflow_classes.get(request.workflow_type)
    if not workflow_class:
        raise HTTPException(
            status_code=404,
            detail=f"Workflow type '{request.workflow_type}' not found. "
            f"Available: {list(workflow_classes.keys())}",
        )

    ctx = dict(request.context or {})
    ctx["task"] = request.task

    workflow = workflow_class(name=f"{request.workflow_type}_workflow")

    planner = PlannerAgent()
    researcher = ResearchAgent()
    executor = ExecutionAgent()

    for agent in [planner, researcher, executor]:
        workflow.register_agent(agent)

    result = workflow.execute(ctx)

    return WorkflowRunResponse(
        workflow_id=result.workflow_id,
        workflow_name=result.workflow_name,
        status=result.status.value,
        steps_total=result.steps_total,
        steps_succeeded=result.steps_succeeded,
        steps_failed=result.steps_failed,
        outputs=result.outputs,
        errors=result.errors,
        execution_time=result.execution_time,
    )
