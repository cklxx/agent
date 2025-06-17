# SPDX-License-Identifier: MIT

from langgraph.graph import MessagesState

from src.prompts.planner_model import Plan
from src.rag import Resource


class State(MessagesState):
    """State for the agent system, extends MessagesState with next field."""

    # Runtime Variables
    environment_info: str = ""
    workspace: str = ""
    plan: Plan = None
    task_description: str = ""
    recursion_limit: int = 20
    resources: list[Resource] = []
    report: str = ""
    token_usage: dict = ""
