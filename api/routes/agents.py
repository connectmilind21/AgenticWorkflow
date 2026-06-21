"""
Agent API routes.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class AgentRunRequest(BaseModel):
    """Request model for running an agent."""

    agent_type: str
    task: str
    context: dict[str, Any] | None = None
    tools: list[str] | None = None


class AgentRunResponse(BaseModel):
    """Response model for agent execution."""

    agent_id: str
    agent_name: str
    status: str
    output: Any | None = None
    error: str | None = None
    execution_time: float = 0.0
    iterations: int = 0


AGENT_REGISTRY: dict[str, type] = {}


def _get_agent_registry() -> dict[str, type]:
    """Lazily load agent registry."""
    if not AGENT_REGISTRY:
        from agents.coding import CodingAgent
        from agents.coordinator import CoordinatorAgent
        from agents.critic import CriticAgent
        from agents.data_analyst import DataAnalysisAgent
        from agents.executor import ExecutionAgent
        from agents.planner import PlannerAgent
        from agents.researcher import ResearchAgent
        from agents.reviewer import ReviewerAgent

        AGENT_REGISTRY.update(
            {
                "planner": PlannerAgent,
                "researcher": ResearchAgent,
                "data_analyst": DataAnalysisAgent,
                "coder": CodingAgent,
                "reviewer": ReviewerAgent,
                "critic": CriticAgent,
                "executor": ExecutionAgent,
                "coordinator": CoordinatorAgent,
            }
        )
    return AGENT_REGISTRY


@router.get("/", summary="List available agent types")
async def list_agents() -> dict[str, Any]:
    """Return list of available agent types."""
    registry = _get_agent_registry()
    return {
        "agents": [
            {"type": key, "class": cls.__name__}
            for key, cls in registry.items()
        ]
    }


@router.post("/run", summary="Run an agent", response_model=AgentRunResponse)
async def run_agent(request: AgentRunRequest) -> AgentRunResponse:
    """Execute an agent with the given task and context."""
    registry = _get_agent_registry()
    agent_class = registry.get(request.agent_type)

    if not agent_class:
        raise HTTPException(
            status_code=404,
            detail=f"Agent type '{request.agent_type}' not found. "
            f"Available: {list(registry.keys())}",
        )

    agent = agent_class()
    result = agent.run(request.task, request.context)

    return AgentRunResponse(
        agent_id=result.agent_id,
        agent_name=result.agent_name,
        status=result.status.value,
        output=result.output,
        error=result.error,
        execution_time=result.execution_time,
        iterations=result.iterations,
    )


@router.get("/{agent_type}", summary="Get agent info")
async def get_agent_info(agent_type: str) -> dict[str, Any]:
    """Get information about a specific agent type."""
    registry = _get_agent_registry()
    agent_class = registry.get(agent_type)

    if not agent_class:
        raise HTTPException(
            status_code=404,
            detail=f"Agent type '{agent_type}' not found.",
        )

    return {
        "type": agent_type,
        "class": agent_class.__name__,
        "description": agent_class.__doc__ or "",
    }
