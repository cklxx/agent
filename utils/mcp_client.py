import asyncio
import logging
from typing import Any, Dict, List, Optional
import json

from utils.dict_object import DictObject
from utils.config import config

# 需要用户自行安装 mcp 相关依赖
try:
    from mcp import ClientSession, StdioServerParameters, stdio_client
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    logging.warning("MCP SDK not available. External MCP server functionality will be disabled.")

# --- MCP Get Tools (Command Server) ---
def mcp_get_tools(command: Optional[str] = None, args: Optional[List[str]] = None, env: Optional[Dict[str, str]] = None):
    """Get available tools from an MCP command server using StdioClient.
       Returns a list of DictObject tool objects."""
    if not MCP_AVAILABLE:
        logging.warning("MCP SDK not available, skipping tool discovery.")
        return []

    async def _get_tools():
        # 确保command和args不为空
        if command is None or args is None:
             logging.error("Command or args is missing for StdioServerParameters.")
             return []
        server_params = StdioServerParameters(
            command=command,
            args=args,
            env=env # Pass env here
        )

        try:
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools_response = await session.list_tools()
                    # 将MCP工具响应转换为DictObject列表
                    return [DictObject(tool.dict()) for tool in tools_response.tools] # 假设MCP工具对象有dict()方法
        except Exception as e:
            logging.error(f"❌ Error getting tools from MCP command server: {e}")
            return []

    # 在asyncio事件循环中运行async函数
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError: # No running loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(_get_tools())

# --- MCP Call Tool ---
def mcp_call_tool(command: Optional[str] = None, args: Optional[List[str]] = None, tool_name: Optional[str] = None, arguments: Optional[Dict[str, Any]] = None, env: Optional[Dict[str, str]] = None):
    """Call a tool on an MCP server using StdioClient."""
    if not MCP_AVAILABLE:
        logging.warning("MCP SDK not available, skipping tool call.")
        return "Error: MCP SDK not available."

    async def _call_tool():
        # 确保command, args, tool_name, arguments不为空
        if command is None or args is None or tool_name is None or arguments is None:
            logging.error("Error: Missing parameters for MCP tool call using StdioClient.")
            return "Error: Missing parameters for tool call."

        # 如果传入的是工具对象而不是工具名称，提取工具名称
        if isinstance(tool_name, dict) and "name" in tool_name:
            actual_tool_name = tool_name["name"]
            logging.info(f"从工具对象中提取工具名称: {actual_tool_name}")
        else:
            actual_tool_name = tool_name

        server_params = StdioServerParameters(
            command=command,
            args=args,
            env=env # Pass env here
        )

        try:
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    try:
                        logging.info(f"调用工具: {actual_tool_name}")
                        result = await session.call_tool(actual_tool_name, arguments)
                        if not result or not result.content:
                            logging.error(f"Empty result from tool call: {actual_tool_name}")
                            return f"Error: Empty result from tool {actual_tool_name}"
                        return result.content[0].text
                    except Exception as e:
                        logging.error(f"❌ Error during tool execution {actual_tool_name}: {str(e)}")
                        if "TaskGroup" in str(e):
                            logging.error("TaskGroup error detected, this might be due to server initialization issues")
                            return f"Error: Server initialization failed for {actual_tool_name}. Please try again."
                        return f"Error executing tool {actual_tool_name}: {str(e)}"
        except Exception as e:
            logging.error(f"❌ Error establishing connection to MCP server: {str(e)}")
            return f"Error: Could not connect to MCP server: {str(e)}"

    # 在asyncio事件循环中运行async函数
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError: # No running loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(_call_tool()) 