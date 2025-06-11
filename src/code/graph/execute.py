# SPDX-License-Identifier: MIT

import logging
import os
from typing import Literal

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command
from langchain_mcp_adapters.client import MultiServerMCPClient

from src.agents import create_agent

from src.config.configuration import Configuration

from .types import State

logger = logging.getLogger(__name__)

# 保持原有的辅助函数
async def execute_agent_step(
    state: State, agent, agent_name: str
) -> Command[Literal["team"]]:
    """Helper function to execute a step using the specified agent."""
    current_plan = state.get("current_plan")
    observations = state.get("observations", [])

    # Find the first unexecuted step
    current_step = None
    completed_steps = []
    for step in current_plan.steps:
        if not (hasattr(step, 'execution_res') and step.execution_res):
            current_step = step
            break
        else:
            completed_steps.append(step)

    if not current_step:
        logger.warning("No unexecuted step found")
        return Command(goto="team")

    logger.info(f"Executing step: {getattr(current_step, 'title', '未知')}, agent: {agent_name}")

    # Format completed steps information
    completed_steps_info = ""
    if completed_steps:
        completed_steps_info = "# 已完成的研究发现\n\n"
        for i, step in enumerate(completed_steps):
            completed_steps_info += f"## 已完成发现 {i + 1}: {getattr(step, 'title', '未知')}\n\n"
            completed_steps_info += f"<finding>\n{getattr(step, 'execution_res', '无结果')}\n</finding>\n\n"

    # Prepare the input for the agent with completed steps info
    agent_input = {
        "messages": [
            HumanMessage(
                content=f"{completed_steps_info}# 当前任务\n\n## 标题\n\n{getattr(current_step, 'title', '未知任务')}\n\n## 描述\n\n{getattr(current_step, 'description', '无描述')}\n\n## 语言环境\n\n{state.get('locale', 'zh-CN')}"
            )
        ]
    }

    # Add citation reminder for researcher agent
    if agent_name == "researcher":
        if state.get("resources"):
            resources_info = "**用户提到的以下资源文件：**\n\n"
            for resource in state.get("resources"):
                resources_info += f"- {resource.title} ({resource.description})\n"

            agent_input["messages"].append(
                HumanMessage(
                    content=resources_info
                    + "\n\n"
                    + "您必须使用 **local_search_tool** 来检索资源文件中的信息。",
                )
            )

        agent_input["messages"].append(
            HumanMessage(
                content="重要提示：不要在文本中包含内联引用。而是跟踪所有来源并在最后包含参考资料部分，使用链接引用格式。引用之间包含空行以提高可读性。对每个引用使用此格式：\n- [来源标题](URL)\n\n- [另一个来源](URL)",
                name="system",
            )
        )

    # Invoke the agent
    default_recursion_limit = 25
    try:
        env_value_str = os.getenv("AGENT_RECURSION_LIMIT", str(default_recursion_limit))
        parsed_limit = int(env_value_str)

        if parsed_limit > 0:
            recursion_limit = parsed_limit
            logger.info(f"Recursion limit set to: {recursion_limit}")
        else:
            logger.warning(
                f"AGENT_RECURSION_LIMIT value '{env_value_str}' (parsed as {parsed_limit}) is not positive. "
                f"Using default value {default_recursion_limit}."
            )
            recursion_limit = default_recursion_limit
    except ValueError:
        raw_env_value = os.getenv("AGENT_RECURSION_LIMIT")
        logger.warning(
            f"Invalid AGENT_RECURSION_LIMIT value: '{raw_env_value}'. "
            f"Using default value {default_recursion_limit}."
        )
        recursion_limit = default_recursion_limit

    logger.info(f"Agent input: {agent_input}")
    try:
        result = await agent.ainvoke(
            input=agent_input, config={"recursion_limit": recursion_limit}
        )
    except Exception as e:
        # 记录详细的API错误信息
        logger.error(f"Agent execution failed for {agent_name}: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")

        # 如果是OpenAI API错误，记录更多详情
        if hasattr(e, "response"):
            logger.error(
                f"API response status: {getattr(e.response, 'status_code', 'Unknown')}"
            )
            logger.error(
                f"API response headers: {dict(getattr(e.response, 'headers', {}))}"
            )
            logger.error(
                f"API response content: {getattr(e.response, 'text', 'No content')}"
            )

        # 如果是httpx错误，也记录详情
        if hasattr(e, "request"):
            logger.error(f"Request URL: {getattr(e.request, 'url', 'Unknown')}")
            logger.error(f"Request body: {getattr(e.request, 'body', 'No body')}")

        raise e

    # Process the result
    response_content = result["messages"][-1].content
    logger.debug(f"{agent_name.capitalize()} full response: {response_content}")

    # Update the step with the execution result
    current_step.execution_res = response_content
    logger.info(f"Step '{getattr(current_step, 'title', '未知')}' execution completed by {agent_name}")

    return Command(
        update={
            "messages": [
                HumanMessage(
                    content=response_content,
                    name=agent_name,
                )
            ],
            "observations": observations + [response_content],
        },
        goto="team",
    )


async def setup_and_execute_agent_step(
    state: State,
    config: RunnableConfig,
    agent_type: str,
    default_tools: list,
) -> Command[Literal["team"]]:
    """Helper function to set up an agent with appropriate tools and execute a step."""
    configurable = Configuration.from_runnable_config(config)
    mcp_servers = {}
    enabled_tools = {}

    # Extract MCP server configuration for this agent type
    if configurable.mcp_settings:
        for server_name, server_config in configurable.mcp_settings["servers"].items():
            if (
                server_config["enabled_tools"]
                and agent_type in server_config["add_to_agents"]
            ):
                mcp_servers[server_name] = {
                    k: v
                    for k, v in server_config.items()
                    if k in ("transport", "command", "args", "url", "env")
                }
                for tool_name in server_config["enabled_tools"]:
                    enabled_tools[tool_name] = server_name

    # Create and execute agent with MCP tools if available
    if mcp_servers:
        async with MultiServerMCPClient(mcp_servers) as client:
            loaded_tools = default_tools[:]
            for tool in client.get_tools():
                if tool.name in enabled_tools:
                    tool.description = (
                        f"Powered by '{enabled_tools[tool.name]}'.\n{tool.description}"
                    )
                    loaded_tools.append(tool)
            agent = create_agent(agent_type, agent_type, loaded_tools, agent_type)
            return await execute_agent_step(state, agent, agent_type)
    else:
        # Use default tools if no MCP servers are configured
        agent = create_agent(agent_type, agent_type, default_tools, agent_type)
        return await execute_agent_step(state, agent, agent_type)
