"""
CLI for the Agentic Workflow Framework.
"""

from __future__ import annotations

import json

import click
from rich.console import Console
from rich.json import JSON
from rich.panel import Panel
from rich.table import Table

console = Console()


@click.group()
@click.version_option(version="0.1.0", prog_name="agentic")
def main() -> None:
    """Agentic Workflow Framework CLI."""


@main.command()
@click.argument("agent_type")
@click.argument("task")
@click.option("--context", "-c", default=None, help="JSON context string")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def run_agent(agent_type: str, task: str, context: str | None, verbose: bool) -> None:
    """Run an agent with the given task."""
    from agents.coding import CodingAgent
    from agents.coordinator import CoordinatorAgent
    from agents.critic import CriticAgent
    from agents.data_analyst import DataAnalysisAgent
    from agents.executor import ExecutionAgent
    from agents.planner import PlannerAgent
    from agents.researcher import ResearchAgent
    from agents.reviewer import ReviewerAgent

    registry = {
        "planner": PlannerAgent,
        "researcher": ResearchAgent,
        "data_analyst": DataAnalysisAgent,
        "coder": CodingAgent,
        "reviewer": ReviewerAgent,
        "critic": CriticAgent,
        "executor": ExecutionAgent,
        "coordinator": CoordinatorAgent,
    }

    agent_class = registry.get(agent_type)
    if not agent_class:
        console.print(f"[red]Unknown agent type: {agent_type}[/red]")
        console.print(f"Available: {', '.join(registry.keys())}")
        raise SystemExit(1)

    ctx = json.loads(context) if context else {}
    agent = agent_class(verbose=verbose)

    with console.status(f"Running [bold]{agent_type}[/bold] agent..."):
        result = agent.run(task, ctx)

    status_color = "green" if result.status.value == "success" else "red"
    console.print(
        Panel(
            f"[{status_color}]Status: {result.status.value}[/{status_color}]\n"
            f"Time: {result.execution_time:.2f}s\n"
            f"Iterations: {result.iterations}",
            title=f"Agent Result: {agent_type}",
        )
    )

    if result.output and verbose:
        console.print(JSON(json.dumps(result.output, default=str)))

    if result.error:
        console.print(f"[red]Error: {result.error}[/red]")


@main.command()
@click.argument("workflow_type", type=click.Choice(["sequential", "parallel", "multi_agent"]))
@click.argument("task")
@click.option("--context", "-c", default=None, help="JSON context string")
def run_workflow(workflow_type: str, task: str, context: str | None) -> None:
    """Run a workflow with the given task."""
    from agents.executor import ExecutionAgent
    from agents.planner import PlannerAgent
    from agents.researcher import ResearchAgent
    from workflows.multi_agent import MultiAgentWorkflow
    from workflows.parallel import ParallelWorkflow
    from workflows.sequential import SequentialWorkflow

    workflow_classes = {
        "sequential": SequentialWorkflow,
        "parallel": ParallelWorkflow,
        "multi_agent": MultiAgentWorkflow,
    }

    ctx = json.loads(context) if context else {}
    ctx["task"] = task

    workflow_class = workflow_classes[workflow_type]
    workflow = workflow_class(name=f"{workflow_type}_workflow")

    for agent in [PlannerAgent(), ResearchAgent(), ExecutionAgent()]:
        workflow.register_agent(agent)

    with console.status(f"Running [bold]{workflow_type}[/bold] workflow..."):
        result = workflow.execute(ctx)

    status_color = "green" if result.status.value == "success" else "yellow"

    table = Table(title=f"Workflow Result: {workflow_type}")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Status", f"[{status_color}]{result.status.value}[/{status_color}]")
    table.add_row("Steps", f"{result.steps_succeeded}/{result.steps_total}")
    table.add_row("Time", f"{result.execution_time:.2f}s")

    console.print(table)

    if result.errors:
        console.print(f"[yellow]Errors:[/yellow] {result.errors}")


@main.command()
def list_agents() -> None:
    """List all available agent types."""
    agents = [
        ("planner", "Decomposes goals into executable plans"),
        ("researcher", "Gathers and synthesizes information"),
        ("data_analyst", "Analyzes data and generates insights"),
        ("coder", "Generates, debugs, and refactors code"),
        ("reviewer", "Reviews and scores outputs"),
        ("critic", "Provides adversarial critiques"),
        ("executor", "Executes tasks using tools"),
        ("coordinator", "Orchestrates multi-agent workflows"),
    ]

    table = Table(title="Available Agents")
    table.add_column("Type", style="bold cyan")
    table.add_column("Description")

    for agent_type, desc in agents:
        table.add_row(agent_type, desc)

    console.print(table)


@main.command()
def serve() -> None:
    """Start the API server."""
    import uvicorn

    console.print("[bold green]Starting Agentic Workflow API...[/bold green]")
    uvicorn.run("api.main:app", host="0.0.0.0", port=8080, reload=True)


if __name__ == "__main__":
    main()
