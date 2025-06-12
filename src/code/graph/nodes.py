# SPDX-License-Identifier: MIT

import json
import logging
import os
import sys
from typing import Literal

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command

from src.agents.agents import create_agent
from src.tools import (
    # 架构师工具
    architect_plan,
    # 代理调度工具
    dispatch_agent,
    # 文件操作工具
    view_file,
    list_files,
    glob_search,
    grep_search,
    edit_file,
    replace_file,
    # 代码执行工具
    python_repl_tool,
    bash_command,
    # 搜索和网络工具
    crawl_tool,
    get_web_search_tool,
    get_retriever_tool,
    # 地图工具
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

from src.config.configuration import Configuration
from src.prompts.template import apply_prompt_template

# 导入上下文管理相关模块
from src.context.intelligent_workspace_analyzer import (
    IntelligentWorkspaceAnalyzer,
)
from .types import State

logger = logging.getLogger(__name__)

# 所有可用工具列表
ALL_TOOLS = [
    # 架构师和代理工具
    architect_plan,
    dispatch_agent,
    # 文件操作工具
    view_file,
    list_files,
    glob_search,
    grep_search,
    edit_file,
    replace_file,
    # 代码执行工具
    python_repl_tool,
    bash_command,
    # 搜索和网络工具
    crawl_tool,
    get_web_search_tool,
    get_retriever_tool,
    # 地图工具
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
]


def context_node(state: State) -> Command[Literal["architect_node"]]:
    """上下文节点：负责环境感知和RAG索引构建"""
    logger.info("🔍 启动上下文分析和环境感知...")

    # 通过系统获取执行环境的信息
    try:

        # 获取任务描述
        user_messages = state.get("messages", [])
        task_description = ""
        if user_messages:
            last_message = user_messages[-1]
            if hasattr(last_message, "content"):
                task_description = last_message.content
            else:
                task_description = str(last_message)

        logger.info(f"📝 分析任务: {task_description[:100]}...")

        # 初始化智能工作区分析器
        analyzer = IntelligentWorkspaceAnalyzer(state.get("workspace", ""))
        # 决定是否需要执行分析
        import asyncio

        environment_result = asyncio.run(analyzer.perform_environment_analysis())

        # 优先使用文本格式的环境信息，如果没有则回退到JSON
        if environment_result.get("success") and environment_result.get("text_summary"):
            environment_info = environment_result["text_summary"]
            logger.info(f"🧠 环境分析完成，使用文本格式结果")
        else:
            # 回退到JSON格式
            environment_info = json.dumps(environment_result, indent=2)
            logger.info(f"🧠 环境分析完成，使用JSON格式结果")

        logger.info("✅ 上下文准备完成，转向架构师节点")

        return Command(
            update={
                "context": [],
                "environment_info": environment_info,
                "task_description": task_description,
            },
            goto="architect_node",
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
            goto="architect_node",
        )


def architect_node(state: State) -> Command[Literal["__end__", "architect_node"]]:
    """架构师节点：基于上下文信息执行主要任务"""
    logger.info("🏗️ 架构师开始执行任务...")

    task_description = state.get("task_description", "Unknown task")

    try:
        # 创建架构师代理
        architect = create_agent(
            agent_name="architect",
            agent_type="architect",
            tools=ALL_TOOLS,
            prompt_template="architect_agent",
        )

        # 构建输入消息
        print(
            f"🔍 任务描述: {task_description} 环境信息: {state.get("environment_info", "Environment information not available")} workspace: {state.get("workspace", "")}"
        )

        # 准备架构师的输入，包含所有必要的状态信息
        architect_input = {
            "messages": apply_prompt_template("architect_agent", state),
            "task_description": state.get("task_description", "Unknown task"),
            "environment_info": state.get(
                "environment_info", "Environment information not available"
            ),
            "workspace": state.get("workspace", ""),
        }

        logger.info("🚀 调用架构师执行任务...")

        # 调用架构师代理
        result = architect.invoke(
            input=architect_input,
            config={"recursion_limit": state.get("max_iterations", 20)},
            debug=True,
        )

        logger.info(f"🔍 架构师返回结果类型: {result.keys()}")
        if result.get("tool_calls", None):
            return Command(
                update={
                    "messages": state.get("messages", []) + result.get("messages", []),
                    "final_report": result.get("tool_calls", []),
                    "execution_completed": True,
                },
                goto="architect_node",
            )
        # 提取响应内容
        final_content = result["messages"][-1].content

        logger.info("✅ 架构师任务执行完成")

        return Command(
            update={
                "final_report": final_content,
                "execution_completed": True,
            },
            goto="__end__",
        )

    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ 架构师节点执行错误: {error_msg}")

        # 特殊处理JWT认证错误
        if "JWT" in error_msg or "token-invalid" in error_msg or "Clerk" in error_msg:
            error_suggestion = (
                f"检测到JWT认证错误: {error_msg}\n\n"
                "可能的解决方案:\n"
                "1. 检查搜索引擎API密钥配置是否正确\n"
                "2. 尝试切换到DuckDuckGo搜索引擎 (无需API密钥)\n"
                "3. 设置环境变量 SEARCH_API=duckduckgo\n"
                "4. 检查网络连接和防火墙设置"
            )
        else:
            error_suggestion = f"执行过程中发生错误: {error_msg}"

        return Command(
            update={
                "final_report": error_suggestion,
                "execution_failed": True,
            },
            goto="__end__",
        )
