from .base_node import BaseNode
from utils.mcp_utils import get_tools
from utils.logger import mcp_logger

class GetToolsNode(BaseNode):
    """获取可用工具"""
    def __call__(self, state: dict) -> dict:
        mcp_logger.info(f"🔍 [GetToolsNode] 开始获取工具...")
        try:
            tools = get_tools()
            mcp_logger.info(f"🔍 [GetToolsNode] 获取到 {len(tools)} 个工具")
            
            # 保持工具的完整信息
            state["tools"] = tools
            
            # 准备工具信息用于提示
            tool_info = []
            for tool in tools:
                # 获取工具的所有必要信息
                name = tool.get("name", "Unknown Tool")
                description = tool.get("description", "No description")
                input_schema = tool.get("inputSchema", {})
                server_name = tool.get("server_name", "local")
                
                # 格式化工具信息
                tool_info.append(f"- {server_name}.{name}: {description}")
                if input_schema:
                    properties = input_schema.get("properties", {})
                    required = input_schema.get("required", [])
                    for param_name, param_info in properties.items():
                        param_type = param_info.get("type", "unknown")
                        req_status = "(Required)" if param_name in required else "(Optional)"
                        tool_info.append(f"    - {param_name} ({param_type}): {req_status}")
            
            state["tool_info_for_prompt"] = "\n".join(tool_info)
            state["selected_tools"] = []  # 初始化选中的工具列表
            state["tool_results"] = []    # 初始化工具执行结果列表
            state["need_more_tools"] = False
            state["tool_call_count"] = 0  # 初始化工具调用次数
            
            mcp_logger.debug(f"🔍 [GetToolsNode] 更新后的状态: {state}")
            return state
        except Exception as e:
            mcp_logger.error(f"❌ [GetToolsNode] 获取工具时出错: {e}")
            state["tools"] = []
            state["tool_info_for_prompt"] = "No tools available."
            state["selected_tools"] = []
            state["tool_results"] = []
            state["need_more_tools"] = False
            state["tool_call_count"] = 0
            return state 