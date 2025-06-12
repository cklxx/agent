# SPDX-License-Identifier: MIT

import logging
import os
from typing import Literal

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

from .types import State

logger = logging.getLogger(__name__)

# 所有可用工具列表
ALL_TOOLS = [
    # 架构规划工具
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
    # # 地图工具
    # search_location,
    # get_route,
    # get_nearby_places,
    # 笔记本工具
    notebook_read,
    notebook_edit_cell,
    # 对话管理工具
    clear_conversation,
    compact_conversation,
    # 思考工具
    think,
]


def context_node(
    state: State, config: RunnableConfig
) -> Command[Literal["architect_node"]]:
    """Context manager node - 初始化上下文管理和环境信息"""
    logger.info("🔧 Context节点：初始化上下文管理和环境信息")

    # 获取配置信息
    configurable = Configuration.from_runnable_config(config)
    # 初始化环境信息
    environment_info = {
        "current_directory": state.get("workspace", os.getcwd()),
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
            "recursion_depth": 0,  # 初始化递归深度
            "max_recursion_depth": 5,  # 最大递归深度
        },
        goto="architect_node",
    )


def architect_node(
    state: State, config: RunnableConfig
) -> Command[Literal["__end__"]]:
    """
    智能架构师节点 - 单次执行节点，通过self_call工具实现递归能力
    """
    logger.info("🏗️ 架构师节点：分析任务并执行")

    # 获取配置信息
    configurable = Configuration.from_runnable_config(config)
    
    # 构建动态工具列表（包含需要配置的工具）
    dynamic_tools = ALL_TOOLS.copy()
    
    # 添加需要配置的搜索工具
    try:
        max_search_results = getattr(configurable, 'max_search_results', 5)
        search_tool = get_web_search_tool(max_search_results)
        dynamic_tools.append(search_tool)
        logger.info(f"✅ 成功添加搜索工具，最大结果数: {max_search_results}")
    except Exception as e:
        logger.warning(f"⚠️ 无法添加搜索工具: {e}")
        logger.warning("提示：请检查搜索引擎API密钥配置 (TAVILY_API_KEY, BRAVE_SEARCH_API_KEY等)")
    
    # 添加检索工具（如果有RAG资源）
    resources = state.get("resources", [])
    if resources:
        try:
            retriever_tool = get_retriever_tool(resources)
            if retriever_tool:
                dynamic_tools.append(retriever_tool)
                logger.info(f"✅ 成功添加检索工具，资源数量: {len(resources)}")
        except Exception as e:
            logger.warning(f"⚠️ 无法添加检索工具: {e}")

    # 创建agent
    agent = create_agent("architect", "architect", dynamic_tools, "architect_agent")

    # 构建消息
    messages = state.get("messages", [])
    if not messages:
        messages = [{"role": "user", "content": "请开始处理任务"}]

    # 调用agent执行任务
    try:
        logger.info("🚀 开始执行智能架构师任务...")
        
        # 准备完整的状态信息用于模板渲染
        full_state = {
            "messages": messages,
            "environment_info": state.get("environment_info", {}),
            "rag_context": state.get("rag_context", ""),
            "locale": state.get("locale", "zh-CN"),
            "recursion_depth": state.get("recursion_depth", 0),
            "max_recursion_depth": state.get("max_recursion_depth", 5),
        }
        
        # 应用prompt模板
        formatted_messages = apply_prompt_template("architect_agent", full_state, configurable)
        
        # 调用agent
        result = agent.invoke({"messages": formatted_messages})
        
        # 改进的响应提取逻辑
        final_content = None
        
        # 方法1：从result.messages中提取
        if hasattr(result, 'messages') and result.messages:
            logger.debug(f"🔍 Result包含 {len(result.messages)} 条消息")
            # 倒序查找最后一个AI消息
            for i, msg in enumerate(reversed(result.messages)):
                msg_type = type(msg).__name__
                logger.debug(f"📝 消息 {len(result.messages)-i}: {msg_type}")
                
                if 'AIMessage' in msg_type:
                    if hasattr(msg, 'content') and msg.content and msg.content.strip():
                        final_content = msg.content.strip()
                        logger.info(f"✅ 成功从AIMessage提取响应内容 (长度: {len(final_content)})")
                        break
        
        # 方法2：直接从result.content提取
        if not final_content and hasattr(result, 'content') and result.content:
            final_content = result.content.strip()
            logger.info(f"✅ 成功从result.content提取响应内容 (长度: {len(final_content)})")
        
        # 方法3：从result字典中提取
        if not final_content and isinstance(result, dict):
            if 'content' in result and result['content']:
                final_content = result['content'].strip()
                logger.info(f"✅ 成功从result字典提取响应内容 (长度: {len(final_content)})")
            elif 'messages' in result and result['messages']:
                last_msg = result['messages'][-1]
                if hasattr(last_msg, 'content') and last_msg.content:
                    final_content = last_msg.content.strip()
                    logger.info(f"✅ 成功从result字典消息提取响应内容 (长度: {len(final_content)})")
        
        # 如果仍然没有内容，设置默认消息
        if not final_content:
            logger.warning("⚠️ 无法提取Agent响应内容")
            logger.debug(f"🔍 Result类型: {type(result)}")
            logger.debug(f"🔍 Result属性: {dir(result) if hasattr(result, '__dict__') else 'N/A'}")
            if hasattr(result, '__dict__'):
                logger.debug(f"🔍 Result内容: {result.__dict__}")
            
            final_content = "架构师任务执行完成，但无法提取具体响应内容。可能存在API调用问题或响应格式异常。"

        logger.info("✅ 架构师任务执行完成")
        
        return Command(
            update={
                "final_report": final_content,
                "execution_completed": True,
            },
            goto="__end__"
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
            goto="__end__"
        )
