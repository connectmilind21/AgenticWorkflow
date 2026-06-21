"""
Stock Research Agent Example.

Demonstrates a multi-agent workflow that researches a stock:
1. PlannerAgent creates a research plan
2. ResearchAgent gathers market data and news
3. DataAnalysisAgent analyzes financial metrics
4. ReviewerAgent validates the analysis quality
"""

from __future__ import annotations

from agents.data_analyst import DataAnalysisAgent
from agents.planner import PlannerAgent
from agents.researcher import ResearchAgent
from agents.reviewer import ReviewerAgent
from memory.short_term import ShortTermMemory
from tools.web_search import WebSearchTool
from workflows.base import WorkflowStep
from workflows.sequential import SequentialWorkflow


def create_stock_research_workflow(ticker: str) -> SequentialWorkflow:
    """
    Create a stock research workflow for the given ticker symbol.

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'TSLA').

    Returns:
        Configured SequentialWorkflow ready to execute.
    """
    shared_memory = ShortTermMemory(max_messages=20)
    search_tool = WebSearchTool(provider="mock")

    planner = PlannerAgent(memory=shared_memory)
    researcher = ResearchAgent(tools=[search_tool], memory=shared_memory)
    analyst = DataAnalysisAgent(memory=shared_memory)
    reviewer = ReviewerAgent(memory=shared_memory)

    workflow = SequentialWorkflow(
        name=f"stock_research_{ticker}",
        description=f"Comprehensive stock research for {ticker}",
        stop_on_failure=False,
    )

    workflow.register_agent(planner)
    workflow.register_agent(researcher)
    workflow.register_agent(analyst)
    workflow.register_agent(reviewer)

    workflow.add_step(
        WorkflowStep(
            id="planning",
            name="Research Planning",
            agent_name="PlannerAgent",
            task=f"Create a comprehensive research plan for {ticker} stock analysis",
            inputs={"ticker": ticker},
            outputs=["research_plan"],
        )
    )

    workflow.add_step(
        WorkflowStep(
            id="research",
            name="Market Research",
            agent_name="ResearchAgent",
            task=(
                f"Research {ticker} stock: recent news, earnings, analyst ratings, "
                f"and market sentiment"
            ),
            inputs={"ticker": ticker},
            depends_on=["planning"],
            outputs=["research_results"],
        )
    )

    workflow.add_step(
        WorkflowStep(
            id="analysis",
            name="Financial Analysis",
            agent_name="DataAnalysisAgent",
            task=f"Analyze {ticker} financial metrics: P/E ratio, revenue growth, margins",
            inputs={"ticker": ticker},
            depends_on=["research"],
            outputs=["analysis_results"],
        )
    )

    workflow.add_step(
        WorkflowStep(
            id="review",
            name="Analysis Review",
            agent_name="ReviewerAgent",
            task=f"Review the quality and completeness of the {ticker} stock analysis",
            depends_on=["analysis"],
            outputs=["review_results"],
        )
    )

    return workflow


def run_stock_research(ticker: str) -> dict:
    """
    Run the stock research workflow for a ticker.

    Args:
        ticker: Stock ticker symbol.

    Returns:
        Workflow results dictionary.
    """
    print(f"\n{'='*60}")
    print(f"Stock Research Agent: {ticker}")
    print(f"{'='*60}\n")

    workflow = create_stock_research_workflow(ticker)
    result = workflow.execute(context={"task": f"Research {ticker} stock", "ticker": ticker})

    print(f"Status: {result.status.value}")
    print(f"Steps: {result.steps_succeeded}/{result.steps_total} succeeded")
    print(f"Time: {result.execution_time:.2f}s")

    if result.errors:
        print(f"Errors: {result.errors}")

    return result.model_dump()


if __name__ == "__main__":
    run_stock_research("AAPL")
