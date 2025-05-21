import os
import asyncio
from typing import Any, Dict, List, Optional
import json
import logging
# 导入新的配置模块
from utils.mcp_config import load_mcp_config, CommandServer, URLServer
# 导入 WebCrawler
from tools.crawler import WebCrawler # 确保路径正确

# 读取 mcp 配置（优先 mcp.json）
mcp_config = load_mcp_config()
# 假设MCP总是启用的，如果配置加载失败，则使用默认行为（本地工具）
mcp_servers = mcp_config.mcpServers if mcp_config else {}

# 需要用户自行安装 mcp 相关依赖
try:
    from mcp import ClientSession, StdioServerParameters, stdio_client
    # 也需要导入HTTP客户端相关的类，如果使用官方SDK的HTTP功能
    # from mcp.client.http import HttpClient # 如果官方SDK支持
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

# --- DictObject helper class ---
# 将 DictObject 提前定义，以便 local_get_tools 和 mcp_get_tools 都能使用
class DictObject(dict):
    def __init__(self, data):
        super().__init__(data)
        for key, value in data.items():
            if isinstance(value, dict):
                self[key] = DictObject(value)
            elif isinstance(value, list) and value and isinstance(value[0], dict):
                self[key] = [DictObject(item) for item in value]
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(f"'DictObject' object has no attribute '{key}'")
    # 添加 __repr__ 以便打印时更清晰 (可选)
    def __repr__(self):
        return json.dumps(self, ensure_ascii=False, indent=2)


# --- Local Tools ---
def local_get_tools():
    """Define and return local dummy tools with 'local_dummy' server_name."""
    tools = [
        {
            "name": "add",
            "description": "Add two numbers together",
            "inputSchema": {
                "properties": {
                    "a": {"type": "integer"},
                    "b": {"type": "integer"}
                },
                "required": ["a", "b"]
            }
        },
        {
            "name": "subtract",
            "description": "Subtract b from a",
            "inputSchema": {
                "properties": {
                    "a": {"type": "integer"},
                    "b": {"type": "integer"}
                },
                "required": ["a", "b"]
            }
        },
        # WebCrawler tool schema
        {
            "name": "web_crawler",
            "description": "Crawl a website and extract content",
            "inputSchema": {
                "properties": {
                    "url": {"type": "string", "description": "Starting URL to crawl"},
                    "max_pages": {"type": "integer", "description": "Maximum number of pages to crawl", "default": 10}
                },
                "required": ["url"]
            }
        }
    ]
    # Wrap local tools in DictObject and assign 'local_dummy' server_name
    return [{"tool": DictObject(tool), "server_name": "local_dummy"} for tool in tools]

# Execute the WebCrawler tool locally
def local_call_web_crawler(url: str, max_pages: int = 10):
    """Execute the WebCrawler tool locally."""
    logging.info(f"🔧 Calling local tool 'web_crawler' with url={url}, max_pages={max_pages}")
    try:
        crawler = WebCrawler(base_url=url, max_pages=max_pages)
        results = crawler.crawl()
        # 返回JSON格式的结果
        return json.dumps(results, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"❌ Error executing local web_crawler tool: {e}")
        return f"Error executing web_crawler: {e}"

# --- MCP Get Tools (Command Server) ---
def mcp_get_tools(command: Optional[str] = None, args: Optional[List[str]] = None, env: Optional[Dict[str, str]] = None):
    """Get available tools from an MCP command server using StdioClient.
       Returns a list of DictObject tool objects."""
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

# --- Get Tools (Consolidated) ---
def get_tools():
    """Get available tools from all configured MCP servers and local dummy tools."""
    all_tools_with_server = [] # Store list of dicts: [{'tool': tool_obj, 'server_name': server_name}, ...]

    mcp_config = load_mcp_config()
    mcp_servers = mcp_config.mcpServers if mcp_config else {}

    # 1. Get tools from configured Command Servers
    for name, server in mcp_servers.items():
        if isinstance(server, CommandServer):
             logging.info(f"🔍 Getting tools from configured Command Server '{name}'...")
             if MCP_AVAILABLE:
                try:
                    tools = mcp_get_tools(command=server.command, args=server.args, env=server.env)
                    # Append tools with their server name
                    all_tools_with_server.extend([{"tool": tool, "server_name": name} for tool in tools])
                except Exception as e:
                    logging.error(f"❌ Error getting tools from command server '{name}': {e}")
             else:
                logging.info(f"  Type: Command, MCP SDK not available, skipping '{name}'.")
        elif isinstance(server, URLServer):
             logging.info(f"  Note: Skipping URL server '{name}' for tool discovery as HTTP tool discovery is not fully implemented.")


    # 2. Add local dummy tools
    logging.info("🔍 Adding local dummy tools...")
    local_tools_with_server_info = local_get_tools()
    all_tools_with_server.extend(local_tools_with_server_info)


    logging.info(f"✅ Finished tool discovery. Found {len(all_tools_with_server)} tools.")
    # logging.debug(f"Discovered tools: {all_tools_with_server}") # Optional: log discovered tools

    return all_tools_with_server

# --- Call Tool (Consolidated) ---
def call_tool(server_name: str, tool_name: str, arguments: Dict[str, Any]):
    """Call a specific tool on a specific MCP server or a local dummy tool."""

    # 1. Handle local dummy tools
    if server_name == "local_dummy":
        logging.info(f"🔧 Calling local dummy tool '{tool_name}' with parameters: {arguments}")
        if tool_name == "add":
            a = arguments.get("a")
            b = arguments.get("b")
            if isinstance(a, (int, float)) and isinstance(b, (int, float)): # Allow float for flexibility
                return a + b
            else:
                return f"Error: Invalid arguments for add tool. Expected numbers, got a={a}, b={b}"
        elif tool_name == "subtract":
            a = arguments.get("a")
            b = arguments.get("b")
            if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                return a - b
            else:
                return f"Error: Invalid arguments for subtract tool. Expected numbers, got a={a}, b={b}"
        elif tool_name == "web_crawler":
            url = arguments.get("url")
            max_pages = arguments.get("max_pages", 10) # Use default value
            # Convert max_pages to int just in case it came in as float/string
            try:
                max_pages = int(max_pages)
            except (ValueError, TypeError):
                logging.warning(f"Invalid max_pages value '{max_pages}', using default 10.")
                max_pages = 10

            if isinstance(url, str) and url: # Also check if url is not empty
                 return local_call_web_crawler(url, max_pages)
            else:
                 return f"Error: Invalid arguments for web_crawler tool. Expected non-empty string for url, got {url}"
        else:
            return f"Error: Local dummy tool '{tool_name}' not found."

    # 2. Handle configured MCP servers (Command or URL)
    mcp_config = load_mcp_config() # Reload config (optional, but ensures latest)
    mcp_servers = mcp_config.mcpServers if mcp_config else {}

    server = mcp_servers.get(server_name)

    if not server:
        logging.error(f"Error: MCP server '{server_name}' not found in config for tool call.")
        return f"Error: Server '{server_name}' not found."

    if isinstance(server, CommandServer):
         if MCP_AVAILABLE:
            logging.info(f"🔧 Calling tool '{tool_name}' on command server '{server_name}' with parameters: {arguments}")
            return mcp_call_tool(command=server.command, args=server.args, tool_name=tool_name, arguments=arguments, env=server.env)
         else:
            logging.warning(f"🔧 Type: Command, MCP SDK not available, skipping tool call '{tool_name}' on '{server_name}'.")
            return f"Error: MCP SDK not available for server '{server_name}'."
    elif isinstance(server, URLServer):
        logging.info(f"🔧 Calling tool '{tool_name}' on URL server '{server_name}' with parameters: {arguments}")
        logging.info(f"  Note: HTTP/URL server tool call not fully implemented in this example.")
        return f"Error: Tool call on URL server '{server_name}' not implemented."
    else:
        logging.warning(f"🔧 Unknown server type for '{server_name}' for tool call, skipping.")
        return f"Error: Unknown server type for '{server_name}'."

def mcp_call_tool(command: Optional[str] = None, args: Optional[List[str]] = None, tool_name: Optional[str] = None, arguments: Optional[Dict[str, Any]] = None, env: Optional[Dict[str, str]] = None):
    """Call a tool on an MCP server using StdioClient."""
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