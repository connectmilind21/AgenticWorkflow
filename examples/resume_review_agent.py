"""
Resume Review Agent Example.

Reviews a resume and provides actionable feedback.
"""

from __future__ import annotations

from agents.critic import CriticAgent
from agents.reviewer import ReviewerAgent
from memory.short_term import ShortTermMemory
from workflows.base import WorkflowStep
from workflows.sequential import SequentialWorkflow

SAMPLE_RESUME = """
John Doe
Software Engineer
john.doe@example.com | LinkedIn: linkedin.com/in/johndoe

EXPERIENCE
-----------
Senior Software Engineer | TechCorp | 2020-Present
- Developed microservices using Python and FastAPI
- Led team of 5 engineers
- Improved system performance by 40%

Software Engineer | StartupXYZ | 2018-2020
- Built React frontend applications
- Implemented REST APIs

EDUCATION
---------
BS Computer Science | State University | 2018

SKILLS
------
Python, JavaScript, SQL, Docker, AWS
"""


def run_resume_review(resume_text: str) -> dict:
    """
    Review a resume and provide structured feedback.

    Args:
        resume_text: Resume content as plain text.

    Returns:
        Review and critique results.
    """
    print(f"\n{'='*60}")
    print("Resume Review Agent")
    print(f"{'='*60}\n")

    memory = ShortTermMemory()
    reviewer = ReviewerAgent(memory=memory, pass_threshold=0.6)
    critic = CriticAgent(memory=memory)

    workflow = SequentialWorkflow(
        name="resume_review",
        description="Resume review and feedback",
        stop_on_failure=False,
    )

    workflow.register_agent(reviewer)
    workflow.register_agent(critic)

    workflow.add_step(
        WorkflowStep(
            id="review",
            name="Resume Review",
            agent_name="ReviewerAgent",
            task="Review this resume for quality, completeness, and effectiveness",
            inputs={"artifact": resume_text, "artifact_type": "content"},
        )
    )

    workflow.add_step(
        WorkflowStep(
            id="critique",
            name="Critical Feedback",
            agent_name="CriticAgent",
            task="Provide critical feedback to make the resume stronger",
            inputs={"artifact": resume_text, "artifact_type": "content"},
            depends_on=["review"],
        )
    )

    result = workflow.execute(
        context={
            "task": "Review the provided resume",
            "artifact": resume_text,
            "artifact_type": "content",
        }
    )

    print(f"Status: {result.status.value}")
    print(f"Steps completed: {result.steps_succeeded}/{result.steps_total}")

    review_output = result.outputs.get("review")
    if review_output:
        print(f"\nReview Score: {review_output.get('score', 'N/A')}")
        print(f"Passed: {review_output.get('passed', False)}")

    return result.model_dump()


if __name__ == "__main__":
    run_resume_review(SAMPLE_RESUME)
