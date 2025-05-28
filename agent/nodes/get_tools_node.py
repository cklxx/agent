from .base_node import BaseNode
from agent.utils.mcp_utils import get_tools
from agent.utils.logger import mcp_logger

class GetToolsNode(BaseNode):
    """Get available tools"""
    def __call__(self, state: dict) -> dict:
        mcp_logger.info(f"🔍 [GetToolsNode] Starting to get tools...")
        try:
            tools = get_tools()
            mcp_logger.info(f"🔍 [GetToolsNode] Retrieved {len(tools)} tools")
            
            # Keep complete tool information
            state["tools"] = tools
            
            # Prepare tool information for prompts
            tool_info = []
            for tool in tools:
                # Get all necessary information about the tool
                name = tool.get("name", "Unknown Tool")
                description = tool.get("description", "No description")
                input_schema = tool.get("inputSchema", {})
                server_name = tool.get("server_name", "local")
                
                # Format tool information
                tool_info.append(f"- {server_name}.{name}: {description}")
                if input_schema:
                    properties = input_schema.get("properties", {})
                    required = input_schema.get("required", [])
                    for param_name, param_info in properties.items():
                        param_type = param_info.get("type", "unknown")
                        req_status = "(Required)" if param_name in required else "(Optional)"
                        tool_info.append(f"    - {param_name} ({param_type}): {req_status}")
            
            state["tool_info_for_prompt"] = "\n".join(tool_info)
            state["selected_tools"] = []  # Initialize selected tools list
            state["tool_results"] = []    # Initialize tool execution results list
            state["need_more_tools"] = False
            state["tool_call_count"] = 0  # Initialize tool call count
            
            mcp_logger.debug(f"🔍 [GetToolsNode] Updated state: {state}")
            return state
        except Exception as e:
            mcp_logger.error(f"❌ [GetToolsNode] Error getting tools: {e}")
            state["tools"] = []
            state["tool_info_for_prompt"] = "No tools available."
            state["selected_tools"] = []
            state["tool_results"] = []
            state["need_more_tools"] = False
            state["tool_call_count"] = 0
            return state 