"""
Workflows package for the Agentic Workflow Framework.
"""

from workflows.base import BaseWorkflow, WorkflowResult, WorkflowStatus
from workflows.conditional import ConditionalWorkflow
from workflows.multi_agent import MultiAgentWorkflow
from workflows.parallel import ParallelWorkflow
from workflows.sequential import SequentialWorkflow

__all__ = [
    "BaseWorkflow",
    "WorkflowStatus",
    "WorkflowResult",
    "SequentialWorkflow",
    "ParallelWorkflow",
    "ConditionalWorkflow",
    "MultiAgentWorkflow",
]
