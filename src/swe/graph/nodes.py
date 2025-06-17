# SPDX-License-Identifier: MIT

import logging
from typing import Literal
from langchain_core.messages import HumanMessage
from langgraph.types import Command
from langchain_core.tools import tool

from src.prompts.planner_model import Plan
from src.agents.agents import create_agent
from src.tools import (
    # 代码执行工具
    python_repl_tool,
    # 搜索和网络工具
    crawl_tool,
    get_web_search_tool,
    search_location,
    get_route,
    get_nearby_places,
    # 笔记本工具
    notebook_read,
    notebook_edit_cell,
    # 对话管理工具
    clear_conversation,
    compact_conversation,
    # 思考工具
    think,
)
import asyncio
from src.prompts.template import apply_prompt_template

# 导入上下文管理相关模块
from src.context.intelligent_workspace_analyzer import (
    IntelligentWorkspaceAnalyzer,
)
from src.tools.workspace_tools import get_workspace_tools
from src.swe.graph.types import State
from src.utils.simple_token_tracker import SimpleTokenTracker

logger = logging.getLogger(__name__)

# 创建工具名称到工具对象的映射，便于快速查找
token_tracker = SimpleTokenTracker()
token_tracker.start_session("architect_agent")


def create_architect_plan_tool_factory(
    state: State, agent_type: str, base_tools: list, recursion_limit: int = 20
):
    """
    Factory function to create the 'architect_plan' tool.

    This factory encapsulates the logic for creating a tool that can deploy a
    sub-agent to perform specific tasks. It captures necessary context from
    the parent agent's state and uses it to invoke the sub-agent.

    Args:
        state: The current state of the parent agent's graph.
        base_tools: The list of tools available to the sub-agent.
        agent_type: The type of the sub-agent to be created.
        recursion_limit: The maximum number of recursive calls allowed.

    Returns:
        A configured 'architect_plan' tool instance.
    """

    @tool
    def architect_plan(prompt: str) -> str:
        """
        Deploy an intelligent agent for code exploration, analysis, and modifications.

        Args:
            prompt: Specific task for the agent to perform.

        Returns:
            The sub-agent's analysis, findings, and any improvements made.
        """
        logger.debug(f"🔍 architect_plan prompt: {prompt}")
        agent_input = {
            "messages": state.get("messages", []) + [HumanMessage(content=prompt)],
            "plan": state.get("plan", None),
            "environment_info": state.get("environment_info", ""),
            "task_description": state.get("task_description", ""),
        }
        agent = create_agent(agent_type, agent_type, base_tools, agent_type)
        result = agent.invoke(
            input=agent_input, config={"recursion_limit": recursion_limit}
        )
        logger.debug(f"🔍 architect_plan result: {result}")
        return result["messages"][-1].content

    return architect_plan


def get_workspace_aware_agent_tools(state: State) -> list:
    """
    Helper function to get a complete list of workspace-aware tools for an agent.

    Args:
        state: Current state containing workspace information

    Returns:
        List of tools including both workspace-aware and original tools
    """
    workspace = state.get("workspace", "")
    workspace_tools = get_workspace_tools(workspace)

    other_tools = [
        think,
        crawl_tool,
        get_web_search_tool(3),  # Web search with limit
        search_location,
        get_route,
        get_nearby_places,
        python_repl_tool,
        clear_conversation,
        compact_conversation,
    ]

    return workspace_tools + other_tools


@tool
def plan_tool(
    plan: Plan,
):
    """Plan tool to do plan."""
    return plan


def update_context(state: State):
    """上下文节点：负责环境感知和RAG索引构建"""
    logger.info("🔍 启动上下文分析和环境感知...")

    # 通过系统获取执行环境的信息
    try:

        # 获取任务描述
        user_messages = state.get("messages", [])
        task_description = user_messages[-1].content

        logger.info(f"📝 分析任务: {task_description[:100]}...")

        # 初始化智能工作区分析器
        analyzer = IntelligentWorkspaceAnalyzer(state.get("workspace", ""))
        # 决定是否需要执行分析
        environment_result = asyncio.run(analyzer.perform_environment_analysis())
        environment_info = environment_result["text_summary"]

        state.update(
            {
                "environment_info": environment_info,
                "task_description": task_description,
            }
        )
        logger.info("✅ 上下文准备完成" + str(state))

    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ 上下文节点执行错误: {error_msg}")


def architect_node(state: State) -> Command[Literal["__end__"]]:
    """领导节点：理解用户意图, 产出规划"""
    logger.info("🏗️ 架构师节点开始执行任务...")
    update_context(state)
    task_description = state.get("task_description", "Unknown task")

    base_tools = get_workspace_aware_agent_tools(state)
    agent_type = "architect"

    architect_plan_tool = create_architect_plan_tool_factory(
        state, agent_type, base_tools, recursion_limit=20
    )

    try:
        main_tools = base_tools + [architect_plan_tool]
        # 创建架构师代理
        agent = create_agent(agent_type, agent_type, main_tools, agent_type)
        # 构建输入消息
        print(
            f"🔍 任务描述: {task_description} 环境信息: {state.get("environment_info", "Environment information not available")}"
        )
        messages = apply_prompt_template(agent_type, state)

        agent_input = {
            "messages": messages,
            "environment_info": state.get("environment_info", ""),
            "task_description": task_description,
        }
        # 调用架构师代理
        result = agent.invoke(input=agent_input, config={"recursion_limit": 20})
        logger.info(f"🔍 leader原始响应: {result}")

        # 从响应中提取content字段
        response = result["messages"][-1]
        result_content = response.content

        print(f"🔍 result_content: {result_content}")
        # 记录token使用情况

        usage_metadata = response.usage_metadata
        response_metadata = response.response_metadata
        if usage_metadata is not None:
            token_tracker.add_usage(
                input_tokens=usage_metadata.get("input_tokens", 0),
                output_tokens=usage_metadata.get("output_tokens", 0),
                model=response_metadata.get("model_name", ""),
            )

        return Command(
            update={
                "report": result_content,
            },
            goto="__end__",
        )
    except Exception as e:
        logger.error(f"❌ architect节点执行错误: {e}")
        return Command(
            update={
                "report": f"Error: {e}",
            },
            goto="__end__",
        )
