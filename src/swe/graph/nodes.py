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
token_tracker.start_session("swe_agent")


def create_swe_tool_factory(
    state: State, agent_type: str, base_tools: list, recursion_limit: int = 20
):
    """
    Factory function to create specialized SWE analysis tools.

    This factory creates tools that can deploy specialized agents for specific
    software engineering tasks like code analysis, refactoring, or testing.

    Args:
        state: The current state of the parent agent's graph.
        base_tools: The list of tools available to the sub-agent.
        agent_type: The type of the sub-agent to be created.
        recursion_limit: The maximum number of recursive calls allowed.

    Returns:
        A configured SWE analysis tool instance.
    """

    @tool
    def swe_analyzer(prompt: str) -> str:
        """
        Deploy specialized SWE agent for detailed code analysis and improvement recommendations.

        This tool creates a focused software engineering agent that can:
        - Perform deep code analysis and quality assessment
        - Identify architectural issues and improvement opportunities
        - Generate detailed technical reports with actionable recommendations
        - Suggest refactoring strategies and implementation approaches

        Args:
            prompt: Specific software engineering task or analysis request.

        Returns:
            Detailed analysis results and improvement recommendations.
        """
        logger.debug(f"🔍 SWE Analyzer prompt: {prompt}")
        agent_input = {
            "messages": state.get("messages", []) + [HumanMessage(content=prompt)],
            "plan": state.get("plan", None),
            "environment_info": state.get("environment_info", ""),
            "task_description": state.get("task_description", ""),
            "workspace": state.get("workspace", ""),
        }
        agent = create_agent(agent_type, agent_type, base_tools, agent_type)
        result = agent.invoke(
            input=agent_input, config={"recursion_limit": recursion_limit}
        )
        logger.info(f"🔍 SWE Analyzer result: {result}")
        return result["messages"][-1].content

    return swe_analyzer


def get_swe_specialized_tools(state: State) -> list:
    """
    Get a specialized list of tools optimized for software engineering tasks.

    Args:
        state: Current state containing workspace information

    Returns:
        List of tools including workspace-aware and SWE-specific tools
    """
    workspace = state.get("workspace", "")
    workspace_tools = get_workspace_tools(workspace)

    # Core SWE tools - focused on analysis and code quality
    swe_core_tools = [
        think,
        python_repl_tool,  # For testing code snippets and calculations
        clear_conversation,
        compact_conversation,
    ]

    # Optional web tools for research (limited use in SWE context)
    web_tools = [
        crawl_tool,
        get_web_search_tool(3),
    ]

    return workspace_tools + swe_core_tools + web_tools


@tool
def plan_tool(
    plan: Plan,
):
    """Plan tool to do plan."""
    return plan


def update_swe_context(state: State):
    """SWE上下文节点：负责软件工程环境感知和代码库分析准备"""
    logger.info("🔧 启动SWE上下文分析和环境感知...")

    try:
        # 获取任务描述
        user_messages = state.get("messages", [])
        task_description = (
            user_messages[-1].content if user_messages else "SWE Analysis"
        )

        logger.info(f"📝 SWE任务分析: {task_description[:100]}...")

        # 初始化智能工作区分析器 - 专注于代码库结构
        workspace = state.get("workspace", "")
        if workspace:
            analyzer = IntelligentWorkspaceAnalyzer(workspace)
            # 执行环境分析，重点关注代码结构和依赖
            environment_result = asyncio.run(analyzer.perform_environment_analysis())
            environment_info = environment_result["text_summary"]
        else:
            environment_info = "No workspace specified for SWE analysis"

        state.update(
            {
                "environment_info": environment_info,
                "task_description": task_description,
            }
        )
        logger.info("✅ SWE上下文准备完成")

    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ SWE上下文节点执行错误: {error_msg}")
        state.update(
            {
                "environment_info": f"Context analysis failed: {error_msg}",
                "task_description": "SWE Analysis with limited context",
            }
        )


def architect_node(state: State) -> Command[Literal["__end__"]]:
    """SWE架构师节点：执行软件工程分析和质量评估"""
    logger.info("🏗️ SWE架构师节点开始执行任务...")
    update_swe_context(state)

    task_description = state.get("task_description", "Unknown SWE task")
    workspace = state.get("workspace", "")
    recursion_limit = state.get("recursion_limit", 100)

    base_tools = get_swe_specialized_tools(state)
    agent_type = "swe_architect"  # 使用专门的SWE架构师类型
    swe_analyzer_tool = create_swe_tool_factory(
        state, agent_type, base_tools, recursion_limit=recursion_limit
    )

    try:
        main_tools = base_tools + [swe_analyzer_tool]
        # 创建SWE架构师代理
        agent = create_agent(agent_type, agent_type, main_tools, agent_type)

        # 构建输入消息
        logger.info(f"🔍 SWE任务描述: {task_description}")
        logger.info(f"📂 工作目录: {workspace}")

        messages = apply_prompt_template(agent_type, state)

        agent_input = {
            "messages": messages,
            "environment_info": state.get("environment_info", ""),
            "task_description": task_description,
            "workspace": workspace,
        }

        # 调用SWE架构师代理
        result = agent.invoke(
            input=agent_input, config={"recursion_limit": recursion_limit}
        )

        # 从响应中提取content字段
        response = result["messages"][-1]
        result_content = response.content

        logger.info(f"🔍 SWE分析结果长度: {len(result_content)} 字符")

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
                "execution_completed": True,
            },
            goto="__end__",
        )

    except Exception as e:
        logger.error(f"❌ SWE架构师节点执行错误: {e}")
        return Command(
            update={
                "report": f"SWE Analysis Error: {e}",
                "execution_failed": True,
            },
            goto="__end__",
        )


def code_analyzer_node(state: State) -> Command[Literal["__end__"]]:
    """代码分析师节点：专注深度代码质量分析"""
    logger.info("🔍 代码分析师节点开始执行...")

    task_description = state.get("task_description", "Code Quality Analysis")
    workspace = state.get("workspace", "")
    recursion_limit = state.get("recursion_limit", 100)

    base_tools = get_swe_specialized_tools(state)
    agent_type = "swe_analyzer"  # 使用专门的代码分析师类型

    try:
        # 创建代码分析师代理
        agent = create_agent(agent_type, agent_type, base_tools, agent_type)

        # 专注于代码分析的任务描述
        analysis_task = f"进行深度代码分析: {task_description}"

        messages = apply_prompt_template(agent_type, state)

        agent_input = {
            "messages": messages,
            "environment_info": state.get("environment_info", ""),
            "task_description": analysis_task,
            "workspace": workspace,
        }

        # 调用代码分析师代理
        result = agent.invoke(
            input=agent_input, config={"recursion_limit": recursion_limit}
        )

        response = result["messages"][-1]
        result_content = response.content

        logger.info(f"🔍 代码分析完成，结果长度: {len(result_content)} 字符")

        return Command(
            update={
                "report": result_content,
                "execution_completed": True,
            },
            goto="__end__",
        )

    except Exception as e:
        logger.error(f"❌ 代码分析师节点执行错误: {e}")
        return Command(
            update={
                "report": f"Code Analysis Error: {e}",
                "execution_failed": True,
            },
            goto="__end__",
        )
