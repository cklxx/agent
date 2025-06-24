# SPDX-License-Identifier: MIT

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from src.swe.graph.types import State
from src.swe.graph.nodes import (
    architect_node,
    code_analyzer_node,
)


def _build_base_graph():
    """构建并返回带有基本节点和边的SWE状态图。

    SWE工作流设计：
    1. 单一入口点：architect_node（SWE架构师）
    2. 可选扩展：code_analyzer_node（深度代码分析）
    3. 灵活的工作流支持多种SWE任务
    """
    builder = StateGraph(State)

    # 设置入口点：START → architect
    builder.add_edge(START, "architect")

    # 添加核心SWE节点
    builder.add_node("architect", architect_node)
    builder.add_node("code_analyzer", code_analyzer_node)

    # 主要工作流：architect → END（简化版）
    builder.add_edge("architect", END)

    # 可选工作流：code_analyzer → END（专门的代码分析）
    builder.add_edge("code_analyzer", END)

    return builder


def _build_advanced_graph():
    """构建高级SWE工作流图，支持条件路由和多阶段分析。

    高级工作流特性：
    - 条件路由基于任务类型
    - 多阶段分析流程
    - 智能工作流决策
    """
    builder = StateGraph(State)

    # 设置入口点
    builder.add_edge(START, "architect")

    # 添加所有SWE节点
    builder.add_node("architect", architect_node)
    builder.add_node("code_analyzer", code_analyzer_node)

    # 定义条件路由函数
    def route_after_architect(state: State):
        """根据任务类型决定下一个节点"""
        task = state.get("task_description", "").lower()

        # 检查是否需要深度代码分析
        if any(
            keyword in task
            for keyword in [
                "代码分析",
                "code analysis",
                "质量",
                "quality",
                "重构",
                "refactor",
                "性能",
                "performance",
            ]
        ):
            return "code_analyzer"
        else:
            return "__end__"

    # 添加条件边
    builder.add_conditional_edges(
        "architect",
        route_after_architect,
        {
            "code_analyzer": "code_analyzer",
            "__end__": END,
        },
    )

    # 代码分析完成后直接结束
    builder.add_edge("code_analyzer", END)

    return builder


def build_graph_with_memory():
    """构建并返回带有持久内存的SWE智能体工作流图。

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
    """构建并返回不带持久内存的SWE智能体工作流图。

    此函数使用_build_base_graph()构建基础图，然后直接编译它。
    结果图不会在单独的调用或会话之间保留状态。
    """
    # 构建状态图
    builder = _build_base_graph()
    return builder.compile()


def build_advanced_graph():
    """构建高级SWE工作流图，支持条件路由和多阶段分析。

    Returns:
        编译后的高级SWE工作流图
    """
    builder = _build_advanced_graph()
    return builder.compile()


def build_advanced_graph_with_memory():
    """构建带有持久内存的高级SWE工作流图。

    Returns:
        带有内存的高级SWE工作流图
    """
    memory = MemorySaver()
    builder = _build_advanced_graph()
    return builder.compile(checkpointer=memory)


# 创建默认图实例
graph = build_graph()

# 导出可用的图构建函数
__all__ = [
    "build_graph",
    "build_graph_with_memory",
    "build_advanced_graph",
    "build_advanced_graph_with_memory",
    "graph",
]
