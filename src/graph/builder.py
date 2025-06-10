# SPDX-License-Identifier: MIT

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from .types import State
from .nodes import (
    coordinator_node,
    planner_node,
    reporter_node,
    research_team_node,
    researcher_node,
    coder_node,
    human_feedback_node,
    background_investigation_node,
)


def _build_base_graph():
    """Builds and returns the base state graph with essential nodes and edges.

    This function constructs the foundational LangGraph StateGraph, adding core nodes
    such as 'coordinator', 'planner', 'reporter', 'research_team', 'researcher',
    'coder', 'human_feedback', and 'background_investigator'. It also defines
    the entry point from START to 'coordinator' and the exit point from 'reporter' to END.
    """
    builder = StateGraph(State)
    builder.add_edge(START, "coordinator")
    builder.add_node("coordinator", coordinator_node)
    builder.add_node("background_investigator", background_investigation_node)
    builder.add_node("planner", planner_node)
    builder.add_node("reporter", reporter_node)
    builder.add_node("research_team", research_team_node)
    builder.add_node("researcher", researcher_node)
    builder.add_node("coder", coder_node)
    builder.add_node("human_feedback", human_feedback_node)
    builder.add_edge("reporter", END)
    return builder


def build_graph_with_memory():
    """Builds and returns the agent workflow graph with persistent memory.

    This function first constructs the base graph using _build_base_graph()
    and then compiles it with a MemorySaver checkpointer. This enables the graph
    to retain conversation history and state across multiple invocations,
    facilitating context persistence.
    """
    # use persistent memory to save conversation history
    # TODO: be compatible with SQLite / PostgreSQL
    memory = MemorySaver()

    # build state graph
    builder = _build_base_graph()
    return builder.compile(checkpointer=memory)


def build_graph():
    """Builds and returns the agent workflow graph without persistent memory.

    This function constructs the base graph using _build_base_graph()
    and then compiles it directly. The resulting graph will not retain
    state across separate invocations or sessions.
    """
    # build state graph
    builder = _build_base_graph()
    return builder.compile()


graph = build_graph()
