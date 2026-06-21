"""
News Monitoring Agent Example.

Monitors news for a topic and generates summaries and insights.
"""

from __future__ import annotations

from agents.critic import CriticAgent
from agents.researcher import ResearchAgent
from memory.short_term import ShortTermMemory
from tools.web_search import WebSearchTool
from workflows.base import WorkflowStep
from workflows.sequential import SequentialWorkflow


def run_news_monitoring(topic: str, max_articles: int = 10) -> dict:
    """
    Monitor and summarize news for a topic.

    Args:
        topic: Topic to monitor.
        max_articles: Maximum number of articles to process.

    Returns:
        News summary and insights.
    """
    print(f"\n{'='*60}")
    print(f"News Monitoring Agent: {topic}")
    print(f"{'='*60}\n")

    memory = ShortTermMemory()
    search_tool = WebSearchTool(provider="mock", max_results=max_articles)

    researcher = ResearchAgent(tools=[search_tool], memory=memory)
    critic = CriticAgent(memory=memory)

    workflow = SequentialWorkflow(
        name=f"news_monitor_{topic[:20]}",
        description=f"News monitoring for: {topic}",
        stop_on_failure=False,
    )

    workflow.register_agent(researcher)
    workflow.register_agent(critic)

    workflow.add_step(
        WorkflowStep(
            id="gather",
            name="Gather News",
            agent_name="ResearchAgent",
            task=f"Find and summarize recent news about: {topic}",
            inputs={"query": topic, "max_results": max_articles},
        )
    )

    workflow.add_step(
        WorkflowStep(
            id="critique",
            name="Analyze Coverage",
            agent_name="CriticAgent",
            task=f"Analyze the quality and completeness of news coverage about: {topic}",
            depends_on=["gather"],
        )
    )

    result = workflow.execute(context={"task": f"Monitor news for: {topic}", "topic": topic})

    print(f"Status: {result.status.value}")
    print(f"Time: {result.execution_time:.2f}s")

    return result.model_dump()


if __name__ == "__main__":
    run_news_monitoring("AI regulation 2024")
