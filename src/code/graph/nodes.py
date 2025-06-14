# SPDX-License-Identifier: MIT

import json
import logging
from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import Command
from langchain_core.tools import tool

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

from src.prompts.template import apply_prompt_template

# 导入上下文管理相关模块
from src.context.intelligent_workspace_analyzer import (
    IntelligentWorkspaceAnalyzer,
)
from src.tools.workspace_tools import get_workspace_tools
from src.utils.json_utils import repair_json_output
from src.code.graph.types import State

logger = logging.getLogger(__name__)

# 创建工具名称到工具对象的映射，便于快速查找


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

    # Convert tools dictionary to list
    workspace_tool_list = list(workspace_tools.values())

    other_tools = [
        think,
        crawl_tool,
        get_web_search_tool(5),  # Web search with limit
        search_location,
        get_route,
        get_nearby_places,
        python_repl_tool,
        clear_conversation,
        compact_conversation,
    ]

    return workspace_tool_list + other_tools


@tool
def plan_tool(
    plan: Plan,
):
    """Plan tool to do plan."""
    return plan


def context_node(state: State) -> Command[Literal["leader"]]:
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
        import asyncio

        environment_result = asyncio.run(analyzer.perform_environment_analysis())
        environment_info = environment_result["text_summary"]

        logger.info("✅ 上下文准备完成，转向架构师节点")

        return Command(
            update={
                "context": [],
                "plan_iterations": 0,
                "environment_info": environment_info,
                "task_description": task_description,
            },
            goto="leader",
        )

    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ 上下文节点执行错误: {error_msg}")

        return Command(
            update={
                "context": [],
                "environment_info": environment_info,
                "task_description": task_description,
            },
            goto="leader",
        )


def leader_node(state: State) -> Command[Literal["__end__", "team"]]:
    """领导节点：理解用户意图, 产出规划"""
    logger.info("🏗️ 领导节点开始执行任务...")
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
        llm = get_llm_by_type(AGENT_LLM_MAP[agent_type])
        logger.info(f"🔧 创建LLM: {llm}")
        all_tools = get_workspace_aware_agent_tools(state)
        # 先绑定工具
        llm = llm.bind_tools(all_tools)
        logger.info("🔧 工具绑定完成")

        # 构建输入消息
        print(
            f"🔍 任务描述: {task_description} 环境信息: {state.get("environment_info", "Environment information not available")}"
        )
        messages = apply_prompt_template(agent_type, state)
        observations = state.get("observations", [])
        plan = state.get("plan", None)
        if plan is not None and len(observations) >= len(plan.steps):
            messages += [
                HumanMessage(content=f"# Existing Observations\n\n{observations[-1]}")
            ]
        logger.info(f"🔧 构建的消息: {messages}")

        logger.info("🚀 leader执行任务...")

        # 调用架构师代理
        response = llm.invoke(messages)
        logger.info(f"🔍 leader原始响应: {response}")

        # 从响应中提取content字段
        if hasattr(response, "content"):
            plan_content = response.content
        else:
            full_response = response.model_dump_json(indent=4, exclude_none=True)
            response_data = json.loads(full_response)
            plan_content = response_data.get("content", full_response)

        # 解析计划内容
        try:
            plan_json = repair_json_output(plan_content)
            logger.info(f"🔍 leader执行结果: {plan_json}")

            current_plan = Plan.model_validate(json.loads(plan_json))
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"❌ JSON解析失败: {e}")
            logger.error(f"原始内容: {plan_content}")
            logger.error(f"修复后内容: {plan_json}")
            raise ValueError(f"无法解析leader的响应为有效的JSON格式: {e}")
        if state.get("execution_completed"):
            return Command(
                update={
                    "report": current_plan.report,
                },
                goto="__end__",
            )

        logger.info("✅ leader执行完成")

        return Command(
            update={
                "plan": current_plan,
                "plan_iterations": plan_iterations + 1,
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
            },
            goto="__end__",
        )


def team_node(
    state: State,
) -> Command[Literal["leader", "execute"]]:
    """Research team node that collaborates on tasks."""
    logger.info("Research team is collaborating on tasks.")
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
        "messages": [
            HumanMessage(
                content=f"{completed_steps_info}# Current Task\n\n## Title\n\n{current_step.title}\n\n## Description\n\n{current_step.description}\n\n## Locale\n\n{state.get('locale', 'en-US')}"
            )
        ]
    }
    # Invoke the agent
    default_recursion_limit = 20
    result = agent.invoke(
        input=agent_input, config={"recursion_limit": default_recursion_limit}
    )
    logger.info(f"🔍 执行代理节点执行结果: {result}")
    observations = state.get("observations", [])

    response_content = result["messages"][-1].content

    logger.debug(f"execute full response: {response_content}")
    # Update the step with the execution result
    current_step.execution_res = response_content
    return Command(
        update={
            "observations": observations + [response_content],
            "plan": current_plan,
        },
        goto="team",
    )
