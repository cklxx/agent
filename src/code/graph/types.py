# SPDX-License-Identifier: MIT

from langgraph.graph import MessagesState

from src.prompts.planner_model import Plan
from src.rag import Resource
from src.utils.simple_token_tracker import SimpleTokenTracker


class State(MessagesState):
    """State for the agent system, extends MessagesState with next field."""

    # Runtime Variables
    environment_info: str = ""
    plan_iterations: int = 0
    workspace: str = ""
    plan: Plan = None
    task_description: str = ""
    observations: list[str] = []
    recursion_limit: int = 20
    resources: list[Resource] = []
    report: str = ""
    token_usage: dict = ""
