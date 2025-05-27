from utils.mcp_utils import get_tools, call_tool, load_prompt_template, parse_yaml_response
from utils.config import config, TOOL_CALL_LIMIT
from utils.logger import mcp_logger
import time

class BaseNode:
    """基础节点类，提供共用功能"""
    
    def check_tool_call_limit(self, state: dict) -> bool:
        """检查工具调用次数是否达到限制"""
        tool_call_count = state.get("tool_call_count", 0)
        if tool_call_count >= TOOL_CALL_LIMIT:
            mcp_logger.warning(f"⚠️ 工具调用次数已达到上限（{TOOL_CALL_LIMIT}次）")
            state["need_more_tools"] = False
            state["need_more_reason"] = f"工具调用次数已达到上限（{TOOL_CALL_LIMIT}次）"
            return True
        return False
    
    def format_tool_history(self, tool_history: list) -> str:
        """格式化工具执行历史"""
        if not tool_history:
            return "无工具执行历史"
        
        formatted_history = []
        for i, hist in enumerate(tool_history):
            history_text = f"执行 {i+1}:\n"
            history_text += f"  工具: {hist.get('tool', 'Unknown')}\n"
            history_text += f"  参数: {hist.get('parameters', {})}\n"
            history_text += f"  结果: {hist.get('result', 'No result')}\n"
            history_text += f"  状态: {hist.get('status', 'Unknown')}\n"
            history_text += f"  执行时间: {hist.get('execution_time', 0):.2f}秒\n"
            history_text += f"  原因: {hist.get('reason', 'No reason provided')}"
            formatted_history.append(history_text)
        
        return "\n\n".join(formatted_history) 