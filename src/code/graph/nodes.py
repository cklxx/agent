# SPDX-License-Identifier: MIT

import json
import logging
import os
from typing import Annotated, Literal

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langgraph.types import Command, interrupt

from src.code.graph.execute import setup_and_execute_agent_step
from src.tools.maps import search_location_in_city
from src.tools import (
    crawl_tool,
    get_web_search_tool,
    get_retriever_tool,
    python_repl_tool,
    search_location,
    get_route,
    get_nearby_places,
    read_file,
    read_file_lines,
    get_file_info,
    write_file,
    append_to_file,
    create_new_file,
    generate_file_diff,
    execute_terminal_command,
    get_current_directory,
    list_directory_contents,
    execute_command_background,
    get_background_tasks_status,
    terminate_background_task,
    test_service_command,
)

from src.config.agents import AGENT_LLM_MAP
from src.config.configuration import Configuration
from src.llms.llm import get_llm_by_type
from src.prompts.planner_model import Plan, StepType
from src.prompts.template import apply_prompt_template
from src.utils.json_utils import repair_json_output

from .types import State

logger = logging.getLogger(__name__)

# 设置日志
llm_logger = logging.getLogger("llm_planner")


@tool
def handoff_to_planner(
    task_title: Annotated[str, "The title of the task to be handed off."],
    locale: Annotated[str, "The user's detected language locale (e.g., en-US, zh-CN)."],
):
    """Handoff to planner agent to do plan."""
    # This tool is not returning anything: we're just using it
    # as a way for LLM to signal that it needs to hand off to planner agent
    return


def context_node(
    state: State, config: RunnableConfig
) -> Command[Literal["coordinator"]]:
    """Context manager node - 初始化上下文管理和环境信息"""
    logger.info("🔧 Context节点：初始化上下文管理和环境信息")
    
    # 获取配置信息
    configurable = Configuration.from_runnable_config(config)
    
    # 初始化环境信息
    environment_info = {
        "current_directory": os.getcwd(),
        "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}",
        "platform": os.name
    }
    
    # 初始化RAG上下文（如果配置了资源）
    rag_context = ""
    if configurable.resources:
        rag_context = "Available RAG resources: " + ", ".join([
            f"{res.title} ({res.description})" for res in configurable.resources
        ])
    
    logger.info(f"✅ 环境初始化完成，工作目录: {environment_info['current_directory']}")
    
    return Command(
        update={
            "environment_info": environment_info,
            "rag_context": rag_context,
            "locale": state.get("locale", "zh-CN"),  # 默认中文
            "resources": configurable.resources,
        },
        goto="code_coordinator",
    )


def coordinator_node(
    state: State, config: RunnableConfig
) -> Command[Literal["planner", "__end__"]]:
    """Coordinator node - 根据当前状态选择执行planner或结束"""
    logger.info("🎯 Coordinator节点：分析当前状态，决定下一步行动")
    
    configurable = Configuration.from_runnable_config(config)
    messages = apply_prompt_template("code_coordinator", state)
    
    # 检查是否已有完整的最终报告
    if state.get("final_report") and state.get("final_report").strip():
        logger.info("✅ 检测到最终报告已生成，准备结束流程")
        return Command(goto="__end__")
    
    # 检查是否已完成所有计划步骤
    current_plan = state.get("current_plan")
    if current_plan and hasattr(current_plan, 'steps'):
        all_completed = all(
            hasattr(step, 'execution_res') and step.execution_res 
            for step in current_plan.steps
        )
        if all_completed:
            logger.info("📋 所有计划步骤已完成，跳转到reporter生成最终报告")
            return Command(goto="reporter")
    
    # 调用LLM决定是否需要规划
    response = (
        get_llm_by_type(AGENT_LLM_MAP["coordinator"])
        .bind_tools([handoff_to_planner])
        .invoke(messages)
    )
    
    locale = state.get("locale", "zh-CN")  
    goto = "__end__"

    if len(response.tool_calls) > 0:
        logger.info("🧠 Coordinator决定启动planner进行任务规划")
        goto = "planner"
    else:
        logger.info("🏁 Coordinator决定结束工作流程")

    return Command(
        update={"locale": locale, "resources": configurable.resources},
        goto=goto,
    )


def planner_node(
    state: State, config: RunnableConfig
) -> Command[Literal["team", "reporter"]]:
    """Planner node - 输出计划后到team节点"""
    logger.info("🧠 Planner节点：生成详细执行计划")

    configurable = Configuration.from_runnable_config(config)
    plan_iterations = state.get("plan_iterations", 0)
    messages = apply_prompt_template("code_task_planner", state, configurable)

    # 记录规划相关的输入信息
    if state.get("messages"):
        user_query = state["messages"][-1].content if state["messages"] else "未知查询"
        llm_logger.info(f"📝 用户查询: {user_query[:80]}{'...' if len(user_query) > 80 else ''}")

    logger.debug(f"规划迭代次数: {plan_iterations}")

    # 添加背景调研结果（如果有）
    if (
        plan_iterations == 0
        and state.get("enable_background_investigation")
        and state.get("background_investigation_results")
    ):
        messages += [
            {
                "role": "user",
                "content": (
                    "background investigation results of user query:\n"
                    + state["background_investigation_results"]
                    + "\n"
                ),
            }
        ]
        logger.debug("已添加背景调研结果到规划上下文")

    # 选择合适的LLM
    if AGENT_LLM_MAP["planner"] == "basic":
        llm = get_llm_by_type(AGENT_LLM_MAP["planner"]).with_structured_output(
            Plan,
            method="json_mode",
        )
    else:
        llm = get_llm_by_type(AGENT_LLM_MAP["planner"])

    # 检查是否超过最大规划迭代次数
    if plan_iterations >= configurable.max_plan_iterations:
        logger.warning(f"⚠️ 规划迭代达到上限 ({configurable.max_plan_iterations})，跳转到reporter")
        return Command(goto="reporter")

    llm_logger.info("🧠 LLM正在生成执行计划...")

    # 生成计划
    full_response = ""
    if AGENT_LLM_MAP["planner"] == "basic":
        response = llm.invoke(messages)
        full_response = response.model_dump_json(indent=4, exclude_none=True)
    else:
        response = llm.stream(messages)
        for chunk in response:
            full_response += chunk.content

    logger.debug(f"Planner response: {full_response[:200]}{'...' if len(full_response) > 200 else ''}")

    try:
        curr_plan = json.loads(repair_json_output(full_response))
        
        # 记录规划的核心信息
        steps = curr_plan.get("steps", [])
        llm_logger.info(f"✅ 生成 {len(steps)} 个执行步骤")

        # 详细记录步骤信息
        if steps:
            logger.debug("规划步骤详情:")
            for i, step in enumerate(steps, 1):
                step_type = step.get("step_type", "未知")
                title = step.get("title", "未设置标题")
                description = step.get("description", "未设置描述")
                logger.debug(f"  {i}. [{step_type.upper()}] {title}")
                logger.debug(f"     📖 {description[:60]}{'...' if len(description) > 60 else ''}")

    except json.JSONDecodeError:
        logger.warning("⚠️ 规划输出解析失败：JSON格式错误")
        if plan_iterations > 0:
            return Command(goto="reporter")
        else:
            return Command(goto="__end__")

    # 检查是否有足够上下文直接生成报告
    if curr_plan.get("has_enough_context"):
        logger.info("✅ 上下文充足，直接跳转到reporter生成最终报告")
        new_plan = Plan.model_validate(curr_plan)
        return Command(
            update={
                "messages": [AIMessage(content=full_response, name="planner")],
                "current_plan": new_plan,
                "plan_iterations": plan_iterations + 1,
            },
            goto="code_reporter",
        )

    # 正常情况：需要team执行具体任务
    logger.info("📋 计划生成完成，转交给team执行")
    new_plan = Plan.model_validate(curr_plan)
    
    return Command(
        update={
            "messages": [AIMessage(content=full_response, name="planner")],
            "current_plan": new_plan,
            "plan_iterations": plan_iterations + 1,
        },
        goto="code_team",
    )


def team_node(
    state: State,
) -> Command[Literal["researcher", "coder", "reporter"]]:
    """Team node - 根据任务和状态选择researcher或coder"""
    logger.info("👥 Team节点：分析当前任务，选择合适的执行角色")
    
    current_plan = state.get("current_plan")
    if not current_plan or not hasattr(current_plan, 'steps'):
        logger.warning("⚠️ 没有可执行的计划，返回reporter")
        return Command(goto="reporter")
    
    steps = current_plan.steps
    if not steps:
        logger.warning("⚠️ 计划中没有步骤，返回reporter")
        return Command(goto="reporter")
    
    # 检查是否所有步骤都已完成
    completed_steps = [
        step for step in steps 
        if hasattr(step, 'execution_res') and step.execution_res
    ]
    
    if len(completed_steps) == len(steps):
        logger.info("✅ 所有计划步骤已完成，转到reporter生成最终报告")
        return Command(goto="code_reporter")
    
    # 找到下一个未执行的步骤
    current_step = None
    for step in steps:
        if not (hasattr(step, 'execution_res') and step.execution_res):
            current_step = step
            break
    
    if not current_step:
        logger.info("📋 没有待执行步骤，转到reporter")
        return Command(goto="code_reporter")
    
    # 根据步骤类型选择执行者
    step_type = getattr(current_step, 'step_type', None)
    step_title = getattr(current_step, 'title', '未知任务')
    
    if step_type == StepType.RESEARCH:
        logger.info(f"🔍 选择researcher执行研究任务: {step_title}")
        return Command(goto="code_researcher")
    elif step_type == StepType.PROCESSING:
        logger.info(f"💻 选择coder执行编程任务: {step_title}")
        return Command(goto="code_coder")
    else:
        # 默认情况：基于任务描述智能选择
        description = getattr(current_step, 'description', '').lower()
        if any(keyword in description for keyword in ['搜索', '调研', '查找', '收集', '分析资料', 'research', 'search']):
            logger.info(f"🔍 基于描述选择researcher: {step_title}")
            return Command(goto="code_researcher")
        elif any(keyword in description for keyword in ['编程', '代码', '实现', '开发', '脚本', 'code', 'implement', 'develop']):
            logger.info(f"💻 基于描述选择coder: {step_title}")
            return Command(goto="code_coder")
        else:
            # 默认选择researcher
            logger.info(f"🔍 默认选择researcher执行: {step_title}")
            return Command(goto="code_researcher")


async def researcher_node(
    state: State, config: RunnableConfig
) -> Command[Literal["team", "coordinator"]]:
    """Researcher node - 使用工具查找资料，根据研究结果决定返回team或coordinator"""
    logger.info("🔍 Researcher节点：搜索和收集信息")
    
    configurable = Configuration.from_runnable_config(config)
    
    # 为researcher配置专用工具
    research_tools = [
        get_web_search_tool(configurable.max_search_results),
        crawl_tool,
        search_location,
        search_location_in_city,
        get_route,
        get_nearby_places,
        get_retriever_tool,  # RAG检索工具
        # 添加文件读取工具用于分析现有资料
        read_file,
        read_file_lines,
        get_file_info,
    ]

    result = await setup_and_execute_agent_step(state, config, "code_researcher", research_tools)

    if result.update.get("goto") == "coordinator":
        logger.info("📋 研究结果表明需要重新规划，返回coordinator节点")
        return Command(
            update=result.update,
            goto="coordinator"
        )
    else:
        logger.info("✅ Researcher任务完成，返回team节点继续执行")
        return Command(
            update=result.update,
            goto="team"
        )


async def coder_node(
    state: State, config: RunnableConfig
) -> Command[Literal["team"]]:
    """Coder node - 使用工具查看代码、编写代码、运行命令行，执行完转到team"""
    logger.info("💻 Coder节点：代码分析和开发")
    
    # 为coder配置专用工具
    coding_tools = [
        # 文件操作工具
        read_file,
        read_file_lines,
        get_file_info,
        write_file,
        append_to_file,
        create_new_file,
        generate_file_diff,
        # 终端操作工具
        execute_terminal_command,
        get_current_directory,
        list_directory_contents,
        execute_command_background,
        get_background_tasks_status,
        terminate_background_task,
        test_service_command,
        # 代码执行工具
        python_repl_tool,
        get_retriever_tool,  # 用于查找代码相关文档
    ]

    result = await setup_and_execute_agent_step(state, config, "code_coder", coding_tools)
    
    # 执行完成后返回team进行下一轮决策
    logger.info("✅ Coder任务完成，返回team节点")
    return Command(
        update=result.update,
        goto="team"
    )


def reporter_node(state: State):
    """Reporter node - 输出最终报告"""
    logger.info("📊 Reporter节点：生成最终报告")
    
    current_plan = state.get("current_plan")
    
    # 构建报告输入
    input_ = {
        "messages": [
            HumanMessage(
                f"# 任务执行报告\n\n## 任务标题\n\n{getattr(current_plan, 'title', '未知任务')}\n\n## 任务描述\n\n{getattr(current_plan, 'thought', '无描述')}"
            )
        ],
        "locale": state.get("locale", "zh-CN"),
    }
    
    # 应用reporter模板
    invoke_messages = apply_prompt_template("code_reporter", input_)
    observations = state.get("observations", [])

    # 添加格式要求
    invoke_messages.append(
        HumanMessage(
            content="重要提示：请按照以下格式结构化您的报告：\n\n1. 关键要点 - 最重要发现的要点列表\n2. 概述 - 主题的简要介绍\n3. 详细分析 - 按逻辑组织的部分\n4. 调研说明（可选）- 更全面的报告\n5. 关键引用 - 在最后列出所有参考资料\n\n对于引用，请不要在文本中使用内联引用。而是在最后的'关键引用'部分使用格式：`- [来源标题](URL)`。引用之间请用空行分隔以提高可读性。\n\n优先使用Markdown表格来展示数据和比较。在展示比较数据、统计信息、功能或选项时使用表格。",
            name="system",
        )
    )

    # 添加所有观察结果
    for i, observation in enumerate(observations, 1):
        invoke_messages.append(
            HumanMessage(
                content=f"执行步骤 {i} 的结果：\n\n{observation}",
                name="observation",
            )
        )
    
    logger.debug(f"Reporter输入消息数量: {len(invoke_messages)}")
    
    # 生成最终报告
    response = get_llm_by_type(AGENT_LLM_MAP["reporter"]).invoke(invoke_messages)
    response_content = response.content
    
    logger.info("✅ 最终报告生成完成")
    logger.debug(f"报告长度: {len(response_content)} 字符")

    return {"final_report": response_content}

def human_feedback_node(
    state,
) -> Command[Literal["planner", "team", "reporter", "__end__"]]:
    """人工反馈节点（根据需要可以扩展）"""
    current_plan = state.get("current_plan", "")
    auto_accepted_plan = state.get("auto_accepted_plan", False)
    
    if not auto_accepted_plan:
        feedback = interrupt("请审核计划。")
        
        if feedback and str(feedback).upper().startswith("[EDIT_PLAN]"):
            logger.info("用户要求编辑计划")
            return Command(goto="planner")
        elif feedback and str(feedback).upper().startswith("[ACCEPT]"):
            logger.info("用户接受计划")
            return Command(
                update={"auto_accepted_plan": True},
                goto="team"
            )
        else:
            logger.info("计划被拒绝，结束流程")
            return Command(goto="__end__")
    else:
        logger.info("计划自动接受")
        return Command(goto="team")
