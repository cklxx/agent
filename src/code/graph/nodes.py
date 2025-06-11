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


def _clear_report_state(state: State, keep_plan_iterations: bool = True) -> dict:
    """
    通用的报告状态清理函数

    Args:
        state: 当前状态
        keep_plan_iterations: 是否保持规划迭代计数

    Returns:
        清理后的状态更新字典
    """
    update_dict = {
        "final_report": "",  # 清空之前的报告
        "current_plan": None,  # 重置当前计划
        "observations": [],  # 清空观察结果
    }

    if keep_plan_iterations:
        update_dict["plan_iterations"] = state.get("plan_iterations", 0)
    else:
        update_dict["plan_iterations"] = 0

    return update_dict


def _check_reflection_response(response_content: str) -> tuple[bool, dict]:
    """
    通用的反思响应检查函数

    Args:
        response_content: LLM的原始响应内容

    Returns:
        (需要重新规划, 解析的反思数据)
    """
    try:
        # 使用通用的JSON修复工具
        repaired_json = repair_json_output(response_content)
        parsed_response = json.loads(repaired_json)

        if parsed_response.get("reflection_result") == "need_replanning":
            return True, parsed_response

    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.debug(f"非JSON响应或解析错误，作为正常报告处理: {e}")

    return False, {}


@tool
def handoff_to_planner(
    task_title: Annotated[str, "The title of the task to be handed off."],
    locale: Annotated[str, "The user's detected language locale (e.g., en-US, zh-CN)."],
):
    """Handoff to planner agent to do plan."""
    # This tool is not returning anything: we're just using it
    # as a way for LLM to signal that it needs to hand off to planner agent
    return


@tool
def execute_simple_task(
    task_description: Annotated[
        str, "Description of the simple task to be executed directly."
    ],
    locale: Annotated[str, "The user's detected language locale (e.g., en-US, zh-CN)."],
):
    """Execute simple, straightforward tasks directly without planning overhead."""
    # This tool is not returning anything: we're just using it
    # as a way for LLM to signal that it wants to execute a simple task directly
    return


def context_node(
    state: State, config: RunnableConfig
) -> Command[Literal["code_coordinator"]]:
    """Context manager node - 初始化上下文管理和环境信息"""
    logger.info("🔧 Context节点：初始化上下文管理和环境信息")

    # 获取配置信息
    configurable = Configuration.from_runnable_config(config)

    # 初始化环境信息
    environment_info = {
        "current_directory": os.getcwd(),
        "python_version": (
            f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}"
        ),
        "platform": os.name,
    }

    # 初始化RAG上下文（如果配置了资源）
    rag_context = ""
    if configurable.resources:
        rag_context = "Available RAG resources: " + ", ".join(
            [f"{res.title} ({res.description})" for res in configurable.resources]
        )

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


def code_coordinator_node(
    state: State, config: RunnableConfig
) -> Command[Literal["code_task_planner", "code_coder", "code_reporter", "__end__"]]:
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
    if current_plan and hasattr(current_plan, "steps") and current_plan.steps:
        all_completed = all(
            hasattr(step, "execution_res") and step.execution_res
            for step in current_plan.steps
        )
        if all_completed:
            logger.info("📋 所有计划步骤已完成，跳转到reporter生成最终报告")
            return Command(goto="code_reporter")

    # 调用LLM决定下一步行动
    response = (
        get_llm_by_type(AGENT_LLM_MAP["coordinator"])
        .bind_tools([handoff_to_planner, execute_simple_task])
        .invoke(messages)
    )

    locale = state.get("locale", "zh-CN")

    if len(response.tool_calls) > 0:
        tool_name = response.tool_calls[0]["name"]
        if tool_name == "handoff_to_planner":
            logger.info("🧠 Coordinator决定启动planner进行任务规划")
            goto = "code_task_planner"
        elif tool_name == "execute_simple_task":
            logger.info("⚡ Coordinator决定直接执行简单任务")
            goto = "code_coder"
        else:
            logger.warning(f"⚠️ 未知工具调用: {tool_name}，默认结束流程")
            goto = "__end__"
    else:
        logger.info("🏁 Coordinator决定结束工作流程")
        goto = "__end__"

    return Command(
        update={"locale": locale, "resources": configurable.resources},
        goto=goto,
    )


def code_task_planner_node(
    state: State, config: RunnableConfig
) -> Command[Literal["code_team", "code_reporter"]]:
    """Planner node - 输出计划后到team节点"""
    logger.info("🧠 Planner节点：生成详细执行计划")

    configurable = Configuration.from_runnable_config(config)
    plan_iterations = state.get("plan_iterations", 0)
    messages = apply_prompt_template("code_task_planner", state, configurable)

    # 记录规划相关的输入信息
    if state.get("messages"):
        user_query = state["messages"][-1].content if state["messages"] else "未知查询"
        llm_logger.info(
            f"📝 用户查询: {user_query[:80]}{'...' if len(user_query) > 80 else ''}"
        )

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
        logger.warning(
            f"⚠️ 规划迭代达到上限 ({configurable.max_plan_iterations})，跳转到reporter"
        )
        return Command(goto="code_reporter")

    llm_logger.info("🧠 LLM正在生成执行计划...")

    # 生成计划
    full_response = ""
    curr_plan = None

    if AGENT_LLM_MAP["planner"] == "basic":
        response = llm.invoke(messages)
        # 对于structured output，响应是已验证的Plan对象
        if hasattr(response, "model_dump"):
            # 这是一个Plan对象，我们需要确保它包含locale字段
            curr_plan_dict = response.model_dump()
            # 确保包含locale字段
            if "locale" not in curr_plan_dict:
                curr_plan_dict["locale"] = state.get("locale", "zh-CN")
            # 重新创建Plan对象以便后续使用
            curr_plan = Plan.model_validate(curr_plan_dict)
            full_response = json.dumps(curr_plan_dict, indent=4, ensure_ascii=False)
        else:
            # 备用：如果返回的是JSON字符串
            full_response = response.model_dump_json(indent=4, exclude_none=True)
            curr_plan_dict = json.loads(repair_json_output(full_response))
            if "locale" not in curr_plan_dict:
                curr_plan_dict["locale"] = state.get("locale", "zh-CN")
            curr_plan = Plan.model_validate(curr_plan_dict)
    else:
        response = llm.stream(messages)
        for chunk in response:
            full_response += chunk.content

        # 解析streaming响应
        try:
            curr_plan_dict = json.loads(repair_json_output(full_response))
            # 确保包含必需的locale字段
            if "locale" not in curr_plan_dict:
                curr_plan_dict["locale"] = state.get("locale", "zh-CN")
            # 创建Plan对象
            curr_plan = Plan.model_validate(curr_plan_dict)
        except json.JSONDecodeError:
            logger.warning("⚠️ 规划输出解析失败：JSON格式错误")
            if plan_iterations > 0:
                return Command(goto="code_reporter")
            else:
                return Command(goto="__end__")
        except Exception as e:
            logger.warning(f"⚠️ Plan模型验证失败：{e}")
            if plan_iterations > 0:
                return Command(goto="code_reporter")
            else:
                return Command(goto="__end__")

    logger.debug(
        f"Planner response: {full_response[:200]}{'...' if len(full_response) > 200 else ''}"
    )

    if curr_plan and hasattr(curr_plan, "steps") and curr_plan.steps:
        # 记录规划的核心信息
        steps = curr_plan.steps
        llm_logger.info(f"✅ 生成 {len(steps)} 个执行步骤")

        # 详细记录步骤信息
        logger.debug("规划步骤详情:")
        for i, step in enumerate(steps, 1):
            step_type = step.step_type
            title = step.title
            description = step.description
            logger.debug(f"  {i}. [{step_type.upper()}] {title}")
            logger.debug(
                f"     📖 {description[:60]}{'...' if len(description) > 60 else ''}"
            )
    else:
        logger.warning("⚠️ 无法解析计划内容")
        if plan_iterations > 0:
            return Command(goto="code_reporter")
        else:
            return Command(goto="__end__")

    # 正常情况：需要team执行具体任务
    logger.info("📋 计划生成完成，转交给team执行")

    return Command(
        update={
            "messages": [AIMessage(content=full_response, name="planner")],
            "current_plan": curr_plan,
            "plan_iterations": plan_iterations + 1,
        },
        goto="code_team",
    )


def code_team_node(
    state: State,
) -> Command[Literal["code_researcher", "code_coder", "code_reporter"]]:
    """Team node - 根据任务和状态选择researcher或coder"""
    logger.info("👥 Team节点：分析当前任务，选择合适的执行角色")

    current_plan = state.get("current_plan")
    if not current_plan or not hasattr(current_plan, "steps"):
        logger.warning("⚠️ 没有可执行的计划，返回reporter")
        return Command(goto="code_reporter")

    steps = current_plan.steps
    if not steps:
        logger.warning("⚠️ 计划中没有步骤，返回reporter")
        return Command(goto="code_reporter")

    # 检查是否所有步骤都已完成
    completed_steps = [
        step for step in steps if hasattr(step, "execution_res") and step.execution_res
    ]

    if len(completed_steps) == len(steps):
        logger.info("✅ 所有计划步骤已完成，转到reporter生成最终报告")
        return Command(goto="code_reporter")

    # 找到下一个未执行的步骤
    current_step = None
    for step in steps:
        if not (hasattr(step, "execution_res") and step.execution_res):
            current_step = step
            break

    if not current_step:
        logger.info("📋 没有待执行步骤，转到reporter")
        return Command(goto="code_reporter")

    # 根据步骤类型选择执行者
    step_type = getattr(current_step, "step_type", None)
    step_title = getattr(current_step, "title", "未知任务")

    if step_type == StepType.RESEARCH:
        logger.info(f"🔍 选择researcher执行研究任务: {step_title}")
        return Command(goto="code_researcher")
    elif step_type == StepType.PROCESSING:
        logger.info(f"💻 选择coder执行编程任务: {step_title}")
        return Command(goto="code_coder")
    else:
        # 默认情况：基于任务描述智能选择
        description = getattr(current_step, "description", "").lower()
        if any(
            keyword in description
            for keyword in [
                "搜索",
                "调研",
                "查找",
                "收集",
                "分析资料",
                "research",
                "search",
            ]
        ):
            logger.info(f"🔍 基于描述选择researcher: {step_title}")
            return Command(goto="code_researcher")
        elif any(
            keyword in description
            for keyword in [
                "编程",
                "代码",
                "实现",
                "开发",
                "脚本",
                "code",
                "implement",
                "develop",
            ]
        ):
            logger.info(f"💻 基于描述选择coder: {step_title}")
            return Command(goto="code_coder")
        else:
            # 默认选择researcher
            logger.info(f"🔍 默认选择researcher执行: {step_title}")
            return Command(goto="code_researcher")


async def code_researcher_node(
    state: State, config: RunnableConfig
) -> Command[Literal["code_team", "code_coordinator"]]:
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
        get_nearby_places,  # RAG检索工具
        # 添加文件读取工具用于分析现有资料
        read_file,
        read_file_lines,
        get_file_info,
    ]
    resources = state.get("resources", [])
    if resources:
        retriever_tool = get_retriever_tool(resources)
        if retriever_tool:
            research_tools.append(retriever_tool)
    result = await setup_and_execute_agent_step(
        state, config, "code_researcher", research_tools
    )

    if result.update.get("goto") == "code_coordinator":
        logger.info("📋 研究结果表明需要重新规划，返回coordinator节点")
        return Command(update=result.update, goto="code_coordinator")
    else:
        logger.info("✅ Researcher任务完成，返回team节点继续执行")
        return Command(update=result.update, goto="code_team")


async def code_coder_node(
    state: State, config: RunnableConfig
) -> Command[Literal["code_team"]]:
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
    ]
    resources = state.get("resources", [])
    if resources:
        retriever_tool = get_retriever_tool(resources)
        if retriever_tool:
            coding_tools.append(retriever_tool)

    result = await setup_and_execute_agent_step(
        state, config, "code_coder", coding_tools
    )

    # 执行完成后返回team进行下一轮决策
    logger.info("✅ Coder任务完成，返回team节点")
    return Command(update=result.update, goto="code_team")


def code_reporter_node(state: State) -> Command[Literal["code_coordinator", "__end__"]]:
    """Reporter node - 输出最终报告，包含反思功能"""
    logger.info("📊 Reporter节点：生成最终报告并进行反思评估")

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

    # 添加格式要求和反思指导
    invoke_messages.append(
        HumanMessage(
            content='重要提示：请首先进行反思评估！\n\n1. 仔细评估任务完成质量和测试结果\n2. 如果发现重大问题，请返回JSON格式的重新规划请求\n3. 只有在质量评估通过后，才生成完整的Markdown报告\n\n如果需要重新规划，请严格按照以下JSON格式回复：\n```json\n{\n  "reflection_result": "need_replanning",\n  "issues_identified": ["问题描述1", "问题描述2"],\n  "suggested_improvements": ["改进建议1", "改进建议2"],\n  "reasoning": "详细说明原因"\n}\n```\n\n如果质量评估通过，请生成完整的Markdown报告，包含\'反思与评估\'章节。',
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

    logger.debug(
        f"Reporter原始响应: {response_content[:200]}{'...' if len(response_content) > 200 else ''}"
    )

    # 使用通用函数检查是否是重新规划请求
    need_replanning, reflection_data = _check_reflection_response(response_content)

    if need_replanning:
        logger.info("🔄 Reporter检测到问题，请求重新规划")

        # 记录检测到的问题
        issues = reflection_data.get("issues_identified", [])
        improvements = reflection_data.get("suggested_improvements", [])
        reasoning = reflection_data.get("reasoning", "未提供详细原因")

        logger.info(f"发现的问题: {', '.join(issues)}")
        logger.info(f"建议改进: {', '.join(improvements)}")
        logger.info(f"重新规划原因: {reasoning}")

        # 构建重新规划消息
        replanning_message = f"## 质量评估反馈\n\n"
        replanning_message += f"**评估结果**: 需要重新规划\n\n"
        replanning_message += f"**发现的问题**:\n"
        for issue in issues:
            replanning_message += f"- {issue}\n"
        replanning_message += f"\n**建议改进方向**:\n"
        for improvement in improvements:
            replanning_message += f"- {improvement}\n"
        replanning_message += f"\n**详细原因**: {reasoning}\n"

        # 使用通用函数完整清理之前的状态并重置
        update_dict = _clear_report_state(state, keep_plan_iterations=True)
        update_dict["messages"] = [
            AIMessage(content=replanning_message, name="reporter")
        ]

        return Command(
            update=update_dict, goto="code_coordinator"  # 返回coordinator重新规划
        )

    # 正常情况：生成最终报告
    logger.info("✅ 最终报告生成完成")
    logger.debug(f"报告长度: {len(response_content)} 字符")

    return Command(update={"final_report": response_content}, goto="__end__")


def human_feedback_node(
    state,
) -> Command[Literal["code_task_planner", "code_team", "code_reporter", "__end__"]]:
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
            return Command(update={"auto_accepted_plan": True}, goto="team")
        else:
            logger.info("计划被拒绝，结束流程")
            return Command(goto="__end__")
    else:
        logger.info("计划自动接受")
        return Command(goto="team")
