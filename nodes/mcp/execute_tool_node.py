from .base_node import BaseNode
from utils.mcp_utils import get_tools, load_prompt_template, parse_yaml_response, call_tool
from utils.call_llm import stream_llm
from utils.logger import mcp_logger
import time

class ExecuteToolNode(BaseNode):
    """执行选中的工具"""
    def __call__(self, state: dict) -> dict:
        mcp_logger.info(f"🔧 [ExecuteToolNode] 开始执行工具...")
        mcp_logger.debug(f"🔧 [ExecuteToolNode] 当前状态: {state}")
        
        # 检查工具调用次数是否达到限制
        if self.check_tool_call_limit(state):
            return state
        
        # 获取选中的工具
        selected_tools = state.get("selected_tools", [])
        if not selected_tools:
            mcp_logger.info("没有选中的工具需要执行")
            return state
        
        # 获取所有可用工具
        tools = get_tools()
        tool_map = {t["name"]: t for t in tools}
        
        # 执行每个选中的工具
        for tool_info in selected_tools:
            tool_name = tool_info["name"]
            parameters = tool_info["parameters"]
            reason = tool_info.get("reason", "")
            
            if tool_name not in tool_map:
                mcp_logger.warning(f"工具不存在: {tool_name}")
                continue
            
            tool = tool_map[tool_name]
            mcp_logger.info(f"执行工具: {tool_name}")
            mcp_logger.debug(f"工具参数: {parameters}")
            mcp_logger.debug(f"使用原因: {reason}")
            
            try:
                # 记录开始时间
                start_time = time.time()
                
                # 使用统一的工具调用接口
                server_name = tool.get("server_name", "local")
                result = call_tool(server_name, tool_name, parameters)
                
                # 记录执行时间
                execution_time = time.time() - start_time
                
                # 更新工具调用计数
                state["tool_call_count"] = state.get("tool_call_count", 0) + 1
                
                # 记录执行结果
                tool_result = {
                    "tool": tool_name,
                    "parameters": parameters,
                    "result": result,
                    "execution_time": execution_time,
                    "status": "success",
                    "reason": reason
                }
                
                # 更新工具历史
                tool_history = state.get("tool_history", [])
                tool_history.append(tool_result)
                state["tool_history"] = tool_history
                
                mcp_logger.info(f"工具执行成功: {tool_name}")
                mcp_logger.debug(f"执行结果: {result}")
                
            except Exception as e:
                mcp_logger.error(f"工具执行失败: {tool_name}, 错误: {e}")
                
                # 记录失败结果
                tool_result = {
                    "tool": tool_name,
                    "parameters": parameters,
                    "result": str(e),
                    "execution_time": time.time() - start_time,
                    "status": "error",
                    "reason": reason
                }
                
                # 更新工具历史
                tool_history = state.get("tool_history", [])
                tool_history.append(tool_result)
                state["tool_history"] = tool_history
        
        # 检查是否需要更多工具
        if state.get("tool_call_count", 0) < state.get("tool_call_limit", 5):
            # 加载提示模板
            prompt_template = load_prompt_template("need_more_tools")
            if not prompt_template:
                mcp_logger.error("无法加载提示模板")
                state["need_more_tools"] = False
                return state
            
            # 准备提示词
            question = state.get("question", "")
            thought = state.get("thinking", "")
            tool_history_text = self.format_tool_history(state.get("tool_history", []))
            
            # 格式化提示词
            prompt = prompt_template.format(
                question=question,
                thought=thought,
                tool_history=tool_history_text
            )
            
            # 添加系统提示
            system_prompt = """你是一个工具调用助手。你必须严格按照以下 YAML 格式返回你的响应：

```yaml
thinking: |
    <你的思考过程>
need_more_tools: <true/false>
reason: <你的理由>
```

重要提示：
1. 你必须使用 YAML 格式
2. 你必须包含 thinking、need_more_tools 和 reason 字段
3. need_more_tools 必须是 true 或 false
"""
            
            # 调用 LLM
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
            
            try:
                # 收集流式输出
                full_response = ""
                for chunk in stream_llm(messages, task_type="quick_response"):
                    full_response += chunk
                    print(chunk, end="", flush=True)
                print()
                
                # 解析 YAML 响应
                response_data = parse_yaml_response(full_response)
                mcp_logger.debug(f"解析到的 YAML 数据: {response_data}")
                
                # 更新状态
                state["thinking"] = response_data.get("thinking", "")
                state["need_more_tools"] = response_data.get("need_more_tools", False)
                state["need_more_tools_reason"] = response_data.get("reason", "")
                
                mcp_logger.info(f"是否需要更多工具: {state['need_more_tools']}")
                mcp_logger.debug(f"原因: {state['need_more_tools_reason']}")
                
            except Exception as e:
                mcp_logger.error(f"处理响应时出错: {e}")
                state["need_more_tools"] = False
                state["need_more_tools_reason"] = str(e)
        else:
            state["need_more_tools"] = False
        
        mcp_logger.debug(f"🔧 [ExecuteToolNode] 更新后的状态: {state}")
        return state
    
    def format_tool_history(self, tool_history):
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