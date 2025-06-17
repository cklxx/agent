# SPDX-License-Identifier: MIT

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from src.swe.graph.types import State
from src.swe.graph.nodes import (
    architect_node,
)


def _build_base_graph():
    """构建并返回带有基本节点和边的状态图。"""
    builder = StateGraph(State)

    # 设置入口点：START → context
    builder.add_edge(START, "architect")

    # 添加核心节点
    builder.add_node("architect", architect_node)
    builder.add_edge("architect", END)

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
