# SPDX-License-Identifier: MIT

from langgraph.graph import StateGraph, START
from langgraph.checkpoint.memory import MemorySaver

from .types import State
from .nodes import (
    context_node,
    architect_node,
)


def _build_base_graph():
    """构建并返回带有基本节点和边的状态图。"""
    builder = StateGraph(State)

    # 设置入口点：START → context
    builder.add_edge(START, "context")

    # 添加核心节点
    builder.add_node("context", context_node)
    builder.add_node("architect_node", architect_node)

    # architect_node 可以递归调用自己或结束流程
    # 不设置固定的出口边，让architect_node动态决定流向

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
