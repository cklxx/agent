from .base_node import BaseNode
from utils.mcp_utils import get_tools, load_prompt_template, parse_yaml_response
from utils.call_llm import stream_llm
from utils.logger import mcp_logger

class DecideToolNode(BaseNode):
    """决定使用哪些工具"""
    def __call__(self, state: dict) -> dict:
        mcp_logger.info(f"🔍 [DecideToolNode] 开始决定使用哪些工具...")
        mcp_logger.debug(f"🔍 [DecideToolNode] 当前状态: {state}")
        
        # 检查工具调用次数是否达到限制
        if self.check_tool_call_limit(state):
            return state
        
        # 加载提示模板
        prompt_template = load_prompt_template("decide_tool")
        if not prompt_template:
            mcp_logger.error("无法加载提示模板")
            return state
        
        # 准备提示词
        tool_info = state.get("tool_info_for_prompt", "No tools available.")
        question = state.get("question", "")
        thought = state.get("thinking", "")
        
        # 获取工具执行历史
        tool_history = state.get("tool_history", [])
        tool_history_text = self.format_tool_history(tool_history)
        
        # 格式化提示词
        prompt = prompt_template.format(
            tool_info=tool_info,
            question=question,
            thought=thought,
            tool_history=tool_history_text
        )
        
        # 添加系统提示，确保返回正确的格式
        system_prompt = """你是一个工具调用助手。你必须严格按照以下 YAML 格式返回你的响应：

```yaml
thinking: |
    <你的思考过程>
actions:
    - tool: <server_name.tool_name>
      reason: <使用这个工具的原因>
      parameters:
          <参数名>: <参数值>
```

重要提示：
1. 你必须使用 YAML 格式
2. 你必须包含 thinking 和 actions 字段
3. 如果不需要使用工具，actions 可以是空列表
4. 每个工具调用必须包含 tool、reason 和 parameters 字段
"""
        
        # 调用 LLM
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        try:
            # 收集流式输出
            full_response = ""
            for chunk in stream_llm(messages, task_type="standard_tool_calls"):
                full_response += chunk
                print(chunk, end="", flush=True)
            print()
            
            # 解析 YAML 响应
            response_data = parse_yaml_response(full_response)
            mcp_logger.debug(f"解析到的 YAML 数据: {response_data}")
            
            # 更新状态
            state["thinking"] = response_data.get("thinking", "")
            
            # 处理工具选择
            actions = response_data.get("actions", [])
            selected_tools = []
            
            # 确保 actions 是列表
            if not isinstance(actions, list):
                mcp_logger.error(f"actions 不是列表类型: {type(actions)}")
                actions = []
            
            for action in actions:
                if isinstance(action, dict):
                    tool_name = action.get("tool", "")
                    if not tool_name:
                        mcp_logger.warning(f"工具名称为空: {action}")
                        continue
                        
                    # 处理 server_name.tool_name 格式
                    if "." in tool_name:
                        tool_name = tool_name.split(".")[-1]
                    
                    # 验证工具是否存在
                    tools = get_tools()
                    if not any(t["name"] == tool_name for t in tools):
                        mcp_logger.warning(f"工具不存在: {tool_name}")
                        continue
                    
                    selected_tools.append({
                        "name": tool_name,
                        "parameters": action.get("parameters", {}),
                        "reason": action.get("reason", "")
                    })
            
            state["selected_tools"] = selected_tools
            mcp_logger.info(f"选中的工具: {selected_tools}")
            
            mcp_logger.debug(f"🔍 [DecideToolNode] 更新后的状态: {state}")
            return state
            
        except Exception as e:
            mcp_logger.error(f"❌ [DecideToolNode] 处理响应时出错: {e}")
            state["selected_tools"] = []
            return state 