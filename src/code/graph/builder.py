# SPDX-License-Identifier: MIT

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from .types import State
from .nodes import (
    context_node,
    coordinator_node,
    planner_node,
    reporter_node,
    team_node,
    researcher_node,
    coder_node,
    human_feedback_node,
)


def _build_base_graph():
    """构建并返回带有基本节点和边的状态图。

    此函数构建基础的LangGraph StateGraph，添加核心节点：
    'context', 'coordinator', 'planner', 'reporter', 'team', 'researcher',
    'coder', 'human_feedback'等。定义了从START到'context'的入口点
    和从'reporter'到END的出口点。
    
    节点流转逻辑：
    START → context → coordinator → planner → team → (researcher/coder) → team → reporter → END
    """
    builder = StateGraph(State)
    
    # 设置入口点：START → context
    builder.add_edge(START, "context")
    
    # 添加所有节点
    builder.add_node("context", context_node)
    builder.add_node("code_coordinator", coordinator_node)
    builder.add_node("code_planner", planner_node)
    builder.add_node("code_reporter", reporter_node)
    builder.add_node("code_team", team_node)
    builder.add_node("code_researcher", researcher_node)
    builder.add_node("code_coder", coder_node)
    #目前没有使用
    builder.add_node("human_feedback", human_feedback_node)
    
    # 设置出口点：reporter → END
    builder.add_edge("code_reporter", END)
    
    return builder


def build_graph_with_memory():
    """构建并返回带有持久内存的智能体工作流图。

    此函数首先使用_build_base_graph()构建基础图，然后用MemorySaver检查点器编译它。
    这使得图能够在多次调用之间保留对话历史和状态，促进上下文持久化。
    """
    # 使用持久内存保存对话历史
    # TODO: 兼容SQLite / PostgreSQL
    memory = MemorySaver()

    # 构建状态图
    builder = _build_base_graph()
    return builder.compile(checkpointer=memory)


def build_graph():
    """构建并返回不带持久内存的智能体工作流图。

    此函数使用_build_base_graph()构建基础图，然后直接编译它。
    结果图不会在单独的调用或会话之间保留状态。
    """
    # 构建状态图
    builder = _build_base_graph()
    return builder.compile()


# 创建默认图实例
graph = build_graph()
