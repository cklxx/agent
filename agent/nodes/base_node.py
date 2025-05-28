from agent.utils.mcp_utils import get_tools, call_tool, load_prompt_template, parse_yaml_response
from agent.utils.config import config, TOOL_CALL_LIMIT
from agent.utils.logger import mcp_logger
import time

class BaseNode:
    """Base node class, provides common functionality"""
    
    def check_tool_call_limit(self, state: dict) -> bool:
        """Check if tool call count has reached the limit"""
        tool_call_count = state.get("tool_call_count", 0)
        if tool_call_count >= TOOL_CALL_LIMIT:
            mcp_logger.warning(f"⚠️ Tool call count has reached the limit ({TOOL_CALL_LIMIT} calls)")
            state["need_more_tools"] = False
            state["need_more_reason"] = f"Tool call count has reached the limit ({TOOL_CALL_LIMIT} calls)"
            return True
        return False
    
    def format_tool_history(self, tool_history: list) -> str:
        """Format tool execution history"""
        if not tool_history:
            return "No tool execution history"
        
        formatted_history = []
        for i, hist in enumerate(tool_history):
            history_text = f"Execution {i+1}:\n"
            history_text += f"  Tool: {hist.get('tool', 'Unknown')}\n"
            history_text += f"  Parameters: {hist.get('parameters', {})}\n"
            history_text += f"  Result: {hist.get('result', 'No result')}\n"
            history_text += f"  Status: {hist.get('status', 'Unknown')}\n"
            history_text += f"  Execution time: {hist.get('execution_time', 0):.2f} seconds\n"
            history_text += f"  Reason: {hist.get('reason', 'No reason provided')}"
            formatted_history.append(history_text)
        
        return "\n\n".join(formatted_history) 