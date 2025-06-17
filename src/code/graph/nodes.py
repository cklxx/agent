# SPDX-License-Identifier: MIT

import json
import logging
from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import Command
from langchain_core.tools import tool

from src.context.manager import ContextManager
from src.context.rag_context_manager import RAGContextManager
from src.prompts.planner_model import Plan
from src.agents.agents import create_agent
from src.config.agents import AGENT_LLM_MAP
from src.llms.llm import get_llm_by_type
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
from src.utils.json_utils import repair_json_output
from src.code.graph.types import State
from src.utils.simple_token_tracker import SimpleTokenTracker

logger = logging.getLogger(__name__)

# 创建工具名称到工具对象的映射，便于快速查找
token_tracker = SimpleTokenTracker()
token_tracker.start_session("architect_agent")


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


context_manager_cache = None


def update_context(state: State):
    """上下文节点：负责环境感知和RAG索引构建"""
    logger.info("🔍 启动上下文分析和环境感知...")

    # 通过系统获取执行环境的信息
    try:

        # 获取任务描述
        user_messages = state.get("messages", [])
        task_description = user_messages[-1].content

        # 初始化智能工作区分析器
        analyzer = IntelligentWorkspaceAnalyzer(state.get("workspace", ""))
        # 决定是否需要执行分析
        environment_result = asyncio.run(analyzer.perform_environment_analysis())
        environment_info = environment_result["text_summary"]

        if context_manager_cache is None:
            context_manager_cache = RAGContextManager(
                context_manager=ContextManager(),
                repo_path=".",
                use_enhanced_retriever=True,
            )
        context = asyncio.run(context_manager_cache.get_rag_context_summary_text())
        logger.info(f"🔍 上下文: {context}")

        state.update(
            {
                "environment_info": environment_info,
                "task_description": task_description,
            }
        )
        logger.info("✅ 上下文准备完成")

    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ 上下文节点执行错误: {error_msg}")


def leader_node(state: State) -> Command[Literal["__end__", "team"]]:
    """领导节点：理解用户意图, 产出规划"""
    logger.info("🏗️ 开始规划任务...")
    update_context(state)
    plan_iterations = state.get("plan_iterations", 0)
    task_description = state.get("task_description", "Unknown task")

    agent_type = "leader"
    iterations_limit = 4
    if plan_iterations > iterations_limit:
        return Command(
            update={
                "report": (
                    f"Plan iterations limit reached: {iterations_limit} times, please check the plan and observations. {Plan.model_validate(state.get('plan',{})).report}"
                ),
            },
            goto="__end__",
        )
    try:
        # 创建架构师代理
        ALL_TOOLS = get_workspace_aware_agent_tools(state)
        agent = create_agent("leader", "leader", ALL_TOOLS, "leader")

        messages = apply_prompt_template(agent_type, state)
        observations = state.get("observations", [])
        plan = state.get("plan", None)
        if plan is not None and len(observations) >= len(plan.steps):
            logger.debug(f"🔍 观察: {observations[-1]}")
            all_observations = ""
            for index, observation in enumerate(observations):
                all_observations += f"# Existing Observations {index}\n\n{observation}"
            messages += [HumanMessage(content=all_observations)]
        logger.debug(f"🔧 构建的消息: {messages}")
        agent_input = {
            "messages": messages,
            "plan": plan,
            "observations": observations,
            "environment_info": state.get("environment_info", ""),
            "task_description": task_description,
        }
        # 调用架构师代理
        result = agent.invoke(input=agent_input, config={"recursion_limit": 30})

        # 从响应中提取content字段
        response = result["messages"][-1]
        plan_content = response.content
        logger.debug(f"🔍 leader响应: {response}")
        # 记录token使用情况

        usage_metadata = response.usage_metadata
        response_metadata = response.response_metadata

        token_tracker.add_usage(
            input_tokens=usage_metadata.get("input_tokens", 0),
            output_tokens=usage_metadata.get("output_tokens", 0),
            model=response_metadata.get("model_name", ""),
        )
        current_plan = state.get("plan", None)
        # 解析计划内容
        try:
            plan_json = repair_json_output(plan_content)
            logger.info(f"🔍 leader plan: {plan_json}")

            current_plan = Plan.model_validate(json.loads(plan_json))
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"❌ JSON解析失败: {e}")
            logger.error(f"原始内容: {plan_content}")
            logger.error(f"修复后内容: {plan_json}")
            return Command(
                update={
                    "report": f"{plan_content}",
                    "execution_failed": True,
                    "token_usage": token_tracker.get_current_report(),
                },
                goto="__end__",
            )

        if current_plan.has_enough_context:
            return Command(
                update={
                    "report": current_plan.report,
                    "token_usage": token_tracker.get_current_report(),
                },
                goto="__end__",
            )

        return Command(
            update={
                "plan": current_plan,
                "plan_iterations": plan_iterations + 1,
                "token_usage": token_tracker.get_current_report(),
            },
            goto="team",
        )

    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ leader节点执行错误: {error_msg}")

        return Command(
            update={
                "report": error_msg,
                "execution_failed": True,
                "token_tracker": token_tracker,
            },
            goto="__end__",
        )


def team_node(
    state: State,
) -> Command[Literal["leader", "execute"]]:
    """Research team node that collaborates on tasks."""
    logger.info("Research team is collaborating on tasks.")
    update_context(state)
    current_plan = state.get("plan")
    if not current_plan or not current_plan.steps:
        return Command(
            goto="leader",
        )
    if all(step.execution_res for step in current_plan.steps):
        return Command(goto="leader")
    for step in current_plan.steps:
        if not step.execution_res:
            break
    if step.step_type:
        return Command(goto="execute")
    return Command(goto="leader")


def execute_node(state: State) -> Command[Literal["team"]]:
    """编码节点：基于上下文信息执行主要任务，并输出执行结果报告"""
    logger.info("🚀 编码节点开始执行任务...")

    current_plan = state.get("plan")
    observations = state.get("observations", [])
    # Find the first unexecuted step
    current_step = None
    completed_steps = []
    for step in current_plan.steps:
        if not step.execution_res:
            current_step = step
            break
        else:
            completed_steps.append(step)

    if not current_step:
        logger.warning("No unexecuted step found")
        return Command(goto="research_team")

    logger.info(f"Executing step: {current_step.title}, agent: execute")

    # Format completed steps information
    completed_steps_info = ""
    if completed_steps:
        completed_steps_info = "# Existing Research Findings\n\n"
        for i, step in enumerate(completed_steps):
            completed_steps_info += f"## Existing Finding {i + 1}: {step.title}\n\n"
            completed_steps_info += f"<finding>\n{step.execution_res}\n</finding>\n\n"

    ALL_TOOLS = get_workspace_aware_agent_tools(state)
    agent = create_agent("execute", "execute", ALL_TOOLS, "execute")
    # Prepare the input for the agent with completed steps info
    agent_input = {
        "messages": (
            apply_prompt_template("execute", state)
            + [
                HumanMessage(
                    content=f"{completed_steps_info}# Current Task\n\n## Title\n\n{current_step.title}\n\n## Description\n\n{current_step.description}\n\n## Locale\n\n{state.get('locale', 'en-US')}"
                )
            ]
        )
    }
    logger.info(f"🔍 执行代理节点输入: {len(str(agent_input))}")
    # Invoke the agent
    default_recursion_limit = 30
    result = agent.invoke(
        input=agent_input, config={"recursion_limit": default_recursion_limit}
    )

    observations = state.get("observations", [])

    response = result["messages"][-1]

    logger.info(f"🔍 执行代理节点执行结果: {response.content}")

    response_content = response.content
    usage_metadata = (
        response.usage_metadata if response.usage_metadata is not None else {}
    )
    response_metadata = (
        response.response_metadata if response.response_metadata is not None else {}
    )
    token_tracker.add_usage(
        input_tokens=usage_metadata.get("input_tokens", 0),
        output_tokens=usage_metadata.get("output_tokens", 0),
        model=response_metadata.get("model_name", ""),
    )
    logger.debug(f"execute full response: {response_content}")
    # Update the step with the execution result
    current_step.execution_res = response_content

    return Command(
        update={
            "observations": observations + [response_content],
            "plan": current_plan,
            "token_usage": token_tracker.get_current_report(),
        },
        goto="team",
    )
