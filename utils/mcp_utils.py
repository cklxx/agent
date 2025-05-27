import os
import asyncio
from typing import Any, Dict, List, Optional
import json
import logging
import time
import yaml
# 导入新的配置模块
from utils.mcp_config import get_mcp_config, CommandServer, URLServer
# 导入 WebCrawler
from tools.crawler import WebCrawler # 确保路径正确

from utils.local_tools import get_local_tool_definitions, call_local_tool
from utils.mcp_client import mcp_get_tools, mcp_call_tool

# 添加工具缓存
_tools_cache = None
_last_cache_time = 0
_CACHE_TTL = 300  # 缓存有效期（秒）

# 读取 mcp 配置（优先 mcp.json）
mcp_config = get_mcp_config()
if mcp_config is None:
    logging.warning("⚠️ 无法加载 MCP 配置，将只使用本地工具")
    mcp_servers = {}
else:
    mcp_servers = mcp_config.mcpServers
    logging.info(f"✅ 成功加载 MCP 配置，发现 {len(mcp_servers)} 个服务器")

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
    global _tools_cache, _last_cache_time
    
    # 检查缓存是否有效
    current_time = time.time()
    if _tools_cache is not None and (current_time - _last_cache_time) < _CACHE_TTL:
        logging.info("使用缓存的工具列表")
        return _tools_cache
    
    logging.info("开始获取工具...")
    all_tools = []
    
    # 添加本地工具
    try:
        local_tools = get_local_tool_definitions()
        logging.info(f"找到 {len(local_tools)} 个本地工具")
        for tool in local_tools:
            tool["server_name"] = "local"
            all_tools.append(tool)
            logging.debug(f"添加本地工具: {tool['name']}")
    except Exception as e:
        logging.error(f"获取本地工具失败: {e}")
    
    # 添加 MCP 服务器工具
    if not mcp_servers:
        logging.warning("没有配置 MCP 服务器，跳过远程工具获取")
    else:
        logging.info(f"开始从 {len(mcp_servers)} 个 MCP 服务器获取工具")
        for server_name, server in mcp_servers.items():
            logging.info(f"正在从服务器 '{server_name}' 获取工具...")
            try:
                if isinstance(server, CommandServer):
                    logging.debug(f"服务器 '{server_name}' 是命令服务器，使用命令: {server.command}")
                    if not server.command:
                        logging.error(f"服务器 '{server_name}' 的命令为空")
                        continue
                    server_tools = mcp_get_tools(
                        command=server.command,
                        args=server.args,
                        env=server.env
                    )
                    if not server_tools:
                        logging.warning(f"从服务器 '{server_name}' 未获取到任何工具")
                        continue
                    logging.info(f"从服务器 '{server_name}' 获取到 {len(server_tools)} 个工具")
                    for tool in server_tools:
                        tool["server_name"] = server_name
                        all_tools.append(tool)
                        logging.debug(f"添加远程工具: {tool['name']} (来自服务器: {server_name})")
                elif isinstance(server, URLServer):
                    logging.warning(f"HTTP 服务器工具获取尚未实现: {server_name}")
                    continue
                else:
                    logging.error(f"未知的服务器类型: {type(server)}")
            except Exception as e:
                logging.error(f"获取远程工具失败: {server_name}: {e}")
    
    # 更新缓存
    _tools_cache = all_tools
    _last_cache_time = current_time
    
    logging.info(f"✅ 总共发现 {len(all_tools)} 个工具")
    return all_tools

# --- Call Tool (Consolidated) ---
def call_tool(server_name: str, tool_name: str, arguments: Dict[str, Any], max_retries: int = 3):
    """调用工具。"""
    # 处理本地工具
    if server_name == "local" or server_name == "local_dummy":
        return call_local_tool(tool_name, arguments)

    server = mcp_servers.get(server_name)
    if not server:
        return f"错误: 未找到服务器 '{server_name}'"

    # 如果传入的是工具对象而不是工具名称，提取工具名称
    if isinstance(tool_name, dict) and "name" in tool_name:
        actual_tool_name = tool_name["name"]
        logging.info(f"从工具对象中提取工具名称: {actual_tool_name}")
    else:
        actual_tool_name = tool_name

    if isinstance(server, CommandServer):
        for attempt in range(max_retries):
            try:
                logging.info(f"尝试调用工具 {actual_tool_name} (尝试 {attempt + 1}/{max_retries})")
                result = mcp_call_tool(
                    command=server.command,
                    args=server.args,
                    tool_name=actual_tool_name,
                    arguments=arguments,
                    env=server.env
                )
                if result and not result.startswith("Error:"):
                    return result
                logging.warning(f"工具调用返回错误: {result}")
                if attempt < max_retries - 1:
                    logging.info(f"等待 2 秒后重试...")
                    time.sleep(2)
            except TimeoutError as e:
                logging.error(f"工具调用超时: {str(e)}")
                if attempt < max_retries - 1:
                    logging.info(f"等待 2 秒后重试...")
                    time.sleep(2)
            except Exception as e:
                logging.error(f"工具调用失败: {str(e)}")
                if attempt < max_retries - 1:
                    logging.info(f"等待 2 秒后重试...")
                    time.sleep(2)
        
        return f"错误: 工具调用失败，已重试 {max_retries} 次"
    
    return f"错误: 不支持的服务器类型 '{server_name}'"

# --- MCP Environment Setup ---
def setup_mcp_environment():
    """设置 MCP 环境。"""
    return {**os.environ, "MCP_SERVER_URL": "http://localhost:8080"}

def load_prompt_template(template_name: str) -> str:
    """Load prompt template from file.
    
    Args:
        template_name: Name of the template file (without .txt extension)
        
    Returns:
        str: Template content or empty string if loading fails
    """
    template_path = os.path.join("prompts", f"{template_name}.txt")
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logging.error(f"Error loading prompt template {template_name}: {e}")
        return ""

def parse_yaml_response(response: str) -> dict:
    """解析 LLM 返回的 YAML 格式响应
    
    Args:
        response: LLM 返回的原始响应文本
        
    Returns:
        解析后的 YAML 数据字典
    """
    try:
        # 尝试从响应中提取 YAML 内容
        yaml_content = response
        if "```yaml" in response:
            yaml_start = response.find("```yaml") + len("```yaml")
            yaml_end = response.find("```", yaml_start)
            if yaml_end != -1:
                yaml_content = response[yaml_start:yaml_end].strip()
        elif "```" in response:
            yaml_start = response.find("```") + len("```")
            yaml_end = response.find("```", yaml_start)
            if yaml_end != -1:
                yaml_content = response[yaml_start:yaml_end].strip()
        
        # 如果找不到 YAML 块，尝试直接使用响应
        if not yaml_content:
            yaml_content = response.strip()
        
        # 解析 YAML
        return yaml.safe_load(yaml_content)
    except yaml.YAMLError as e:
        logging.error(f"YAML 解析错误: {e}")
        logging.error(f"原始响应内容: {response}")
        return {} 