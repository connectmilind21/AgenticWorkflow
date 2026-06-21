"""
Financial Analysis Agent Example.

A multi-agent workflow for comprehensive financial analysis:
1. Research financial data (earnings, revenue, cash flow)
2. Analyze financial ratios and trends
3. Generate investment thesis
4. Critic reviews the thesis
"""

from __future__ import annotations

from agents.critic import CriticAgent
from agents.data_analyst import DataAnalysisAgent
from agents.researcher import ResearchAgent
from memory.short_term import ShortTermMemory
from tools.web_search import WebSearchTool
from workflows.multi_agent import MultiAgentWorkflow


def run_financial_analysis(company: str, period: str = "Q4 2024") -> dict:
    """
    Run comprehensive financial analysis for a company.

    Args:
        company: Company name or ticker.
        period: Reporting period.

    Returns:
        Analysis results.
    """
    print(f"\n{'='*60}")
    print(f"Financial Analysis: {company} ({period})")
    print(f"{'='*60}\n")

    shared_memory = ShortTermMemory(max_messages=30)
    search_tool = WebSearchTool(provider="mock")

    researcher = ResearchAgent(tools=[search_tool], memory=shared_memory)
    analyst = DataAnalysisAgent(memory=shared_memory)
    critic = CriticAgent(memory=shared_memory)

    workflow = MultiAgentWorkflow(
        name=f"financial_analysis_{company}",
        description=f"Financial analysis for {company}",
        collaboration_mode="pipeline",
    )

    workflow.register_agent(researcher)
    workflow.register_agent(analyst)
    workflow.register_agent(critic)

    context = {
        "task": (
            f"Analyze {company} financial performance for {period}: "
            f"revenue, earnings, margins, cash flow, and forward guidance"
        ),
        "company": company,
        "period": period,
    }

    result = workflow.execute(context=context)

    print(f"Status: {result.status.value}")
    print(f"Steps: {result.steps_succeeded}/{result.steps_total}")
    print(f"Time: {result.execution_time:.2f}s")

    return result.model_dump()


if __name__ == "__main__":
    run_financial_analysis("Apple Inc.", "Q4 2024")
