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
async def mcp_get_tools_async(command: str, args: List[str], env: Dict[str, str]) -> List[Dict]:
    """异步获取 MCP 工具列表"""
    try:
        # 创建子进程
        process = await asyncio.create_subprocess_exec(
            command,
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env
        )
        
        # 设置超时时间（5秒）
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=5.0)
        except asyncio.TimeoutError:
            process.kill()
            raise TimeoutError("MCP 工具获取超时（5秒）")
        
        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            raise RuntimeError(f"MCP 工具获取失败: {error_msg}")
            
        return [DictObject(tool) for tool in json.loads(stdout.decode())]
    except Exception as e:
        logging.error(f"❌ MCP 工具获取错误: {e}")
        raise

async def mcp_call_tool_async(command: str, args: List[str], tool_name: str, arguments: Dict[str, Any], env: Dict[str, str]) -> Any:
    """异步调用 MCP 工具"""
    try:
        # 创建子进程
        process = await asyncio.create_subprocess_exec(
            command,
            *args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env
        )
        
        # 准备输入数据
        input_data = json.dumps({
            "tool": tool_name,
            "arguments": arguments
        }).encode()
        
        # 设置超时时间（5秒）
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(input_data), timeout=5.0)
        except asyncio.TimeoutError:
            process.kill()
            raise TimeoutError("MCP 工具调用超时（5秒）")
        
        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            raise RuntimeError(f"MCP 工具调用失败: {error_msg}")
            
        return json.loads(stdout.decode())
    except Exception as e:
        logging.error(f"❌ MCP 工具调用错误: {e}")
        raise

def mcp_get_tools(command: str, args: List[str], env: Dict[str, str]) -> List[Dict]:
    """同步获取 MCP 工具列表"""
    return asyncio.run(mcp_get_tools_async(command, args, env))

def mcp_call_tool(command: str, args: List[str], tool_name: str, arguments: Dict[str, Any], env: Dict[str, str]) -> Any:
    """同步调用 MCP 工具"""
    return asyncio.run(mcp_call_tool_async(command, args, tool_name, arguments, env))

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

        server_params = StdioServerParameters(
            command=command,
            args=args,
            env=env # Pass env here
        )

        try:
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(tool_name, arguments)
                    # 假设返回结果在result.content[0].text中
                    return result.content[0].text
        except Exception as e:
            logging.error(f"❌ Error calling tool on MCP command server: {e}")
            return f"Error executing tool: {e}"

    # 在asyncio事件循环中运行async函数
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError: # No running loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(_call_tool()) 