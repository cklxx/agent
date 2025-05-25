import os
import asyncio
from typing import Any, Dict, List, Optional
import json
import logging
# 导入新的配置模块
from utils.mcp_config import load_mcp_config, CommandServer, URLServer
# 导入 WebCrawler
from tools.crawler import WebCrawler # 确保路径正确

from utils.local_tools import get_local_tool_definitions, call_local_tool
from utils.mcp_client import mcp_get_tools, mcp_call_tool

# 读取 mcp 配置（优先 mcp.json）
mcp_config = load_mcp_config()
# 假设MCP总是启用的，如果配置加载失败，则使用默认行为（本地工具）
mcp_servers = mcp_config.mcpServers if mcp_config else {}
from utils.dict_object import DictObject

# 需要用户自行安装 mcp 相关依赖
try:
    from mcp import ClientSession, StdioServerParameters, stdio_client
    # 也需要导入HTTP客户端相关的类，如果使用官方SDK的HTTP功能
    # from mcp.client.http import HttpClient # 如果官方SDK支持
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

# --- Get Tools (Consolidated) ---
def get_tools():
    """获取所有可用工具。"""
    tools = []
    
    # 添加本地工具
    tools.extend([
        {'tool': tool, 'server_name': 'local_dummy'} 
        for tool in get_local_tool_definitions()
    ])
    
    # 添加 MCP 服务器工具
    for name, server in mcp_servers.items():
        if isinstance(server, CommandServer):
            try:
                server_tools = mcp_get_tools(
                    command=server.command,
                    args=server.args,
                    env=server.env
                )
                tools.extend([
                    {"tool": tool, "server_name": name} 
                    for tool in server_tools
                ])
            except Exception as e:
                logging.error(f"❌ 从服务器 '{name}' 获取工具失败: {e}")
    
    logging.info(f"✅ 发现 {len(tools)} 个工具")
    return tools

# --- Call Tool (Consolidated) ---
def call_tool(server_name: str, tool_name: str, arguments: Dict[str, Any]):
    """调用工具。"""
    if server_name == "local_dummy":
        return call_local_tool(tool_name, arguments)
    
    server = mcp_servers.get(server_name)
    if not server:
        return f"错误: 未找到服务器 '{server_name}'"
    
    if isinstance(server, CommandServer):
        return mcp_call_tool(
            command=server.command,
            args=server.args,
            tool_name=tool_name,
            arguments=arguments,
            env=server.env
        )
    
    return f"错误: 不支持的服务器类型 '{server_name}'"
# --- MCP Environment Setup ---
def setup_mcp_environment():
    """设置 MCP 环境。"""
    return {**os.environ, "MCP_SERVER_URL": "http://localhost:8080"} 