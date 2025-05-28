from .base_node import BaseNode
from agent.utils.mcp_utils import get_tools, load_prompt_template, parse_yaml_response, call_tool
from agent.utils.call_llm import stream_llm
from agent.utils.logger import mcp_logger
import time

class ExecuteToolNode(BaseNode):
    """Execute selected tools"""
    def __call__(self, state: dict) -> dict:
        mcp_logger.info(f"🔧 [ExecuteToolNode] Starting to execute tools...")
        mcp_logger.debug(f"🔧 [ExecuteToolNode] Current state: {state}")
        
        # Check if tool call limit has been reached
        if self.check_tool_call_limit(state):
            return state
        
        # Get selected tools
        selected_tools = state.get("selected_tools", [])
        if not selected_tools:
            mcp_logger.info("No selected tools to execute")
            return state
        
        # Get all available tools
        tools = get_tools()
        tool_map = {t["name"]: t for t in tools}
        
        # Execute each selected tool
        for tool_info in selected_tools:
            tool_name = tool_info["name"]
            parameters = tool_info["parameters"]
            reason = tool_info.get("reason", "")
            
            if tool_name not in tool_map:
                mcp_logger.warning(f"Tool does not exist: {tool_name}")
                continue
            
            tool = tool_map[tool_name]
            mcp_logger.info(f"Executing tool: {tool_name}")
            mcp_logger.debug(f"Tool parameters: {parameters}")
            mcp_logger.debug(f"Usage reason: {reason}")
            
            try:
                # Record start time
                start_time = time.time()
                
                # Use unified tool call interface
                server_name = tool.get("server_name", "local")
                result = call_tool(server_name, tool_name, parameters)
                
                # Record execution time
                execution_time = time.time() - start_time
                
                # Update tool call count
                state["tool_call_count"] = state.get("tool_call_count", 0) + 1
                
                # Record execution result
                tool_result = {
                    "tool": tool_name,
                    "parameters": parameters,
                    "result": result,
                    "execution_time": execution_time,
                    "status": "success",
                    "reason": reason
                }
                
                # Update tool history
                tool_history = state.get("tool_history", [])
                tool_history.append(tool_result)
                state["tool_history"] = tool_history
                
                mcp_logger.info(f"Tool execution successful: {tool_name}")
                mcp_logger.debug(f"Execution result: {result}")
                
            except Exception as e:
                mcp_logger.error(f"Tool execution failed: {tool_name}, error: {e}")
                
                # Record failure result
                tool_result = {
                    "tool": tool_name,
                    "parameters": parameters,
                    "result": str(e),
                    "execution_time": time.time() - start_time,
                    "status": "error",
                    "reason": reason
                }
                
                # Update tool history
                tool_history = state.get("tool_history", [])
                tool_history.append(tool_result)
                state["tool_history"] = tool_history
        
        # Check if more tools are needed
        if state.get("tool_call_count", 0) < state.get("tool_call_limit", 5):
            # Load prompt template
            prompt_template = load_prompt_template("need_more_tools")
            if not prompt_template:
                mcp_logger.error("Failed to load prompt template")
                state["need_more_tools"] = False
                return state
            
            # Prepare prompt
            question = state.get("question", "")
            thought = state.get("thinking", "")
            tool_history_text = self.format_tool_history(state.get("tool_history", []))
            
            # Format prompt
            prompt = prompt_template.format(
                question=question,
                thought=thought,
                tool_history=tool_history_text
            )
            
            # Add system prompt
            system_prompt = """You are a tool calling assistant. You must strictly respond in the following YAML format:

```yaml
thinking: |
    <your thinking process>
need_more_tools: <true/false>
reason: <your reasoning>
```

Important notes:
1. You must use YAML format
2. You must include thinking, need_more_tools, and reason fields
3. need_more_tools must be true or false
"""
            
            # Call LLM
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
            
            try:
                # Collect streaming output
                full_response = ""
                for chunk in stream_llm(messages, task_type="quick_response"):
                    full_response += chunk
                    print(chunk, end="", flush=True)
                print()
                
                # Parse YAML response
                response_data = parse_yaml_response(full_response)
                mcp_logger.debug(f"Parsed YAML data: {response_data}")
                
                # Update state
                state["thinking"] = response_data.get("thinking", "")
                state["need_more_tools"] = response_data.get("need_more_tools", False)
                state["need_more_tools_reason"] = response_data.get("reason", "")
                
                mcp_logger.info(f"Need more tools: {state['need_more_tools']}")
                mcp_logger.debug(f"Reason: {state['need_more_tools_reason']}")
                
            except Exception as e:
                mcp_logger.error(f"Error processing response: {e}")
                state["need_more_tools"] = False
                state["need_more_tools_reason"] = str(e)
        else:
            state["need_more_tools"] = False
        
        mcp_logger.debug(f"🔧 [ExecuteToolNode] Updated state: {state}")
        return state
    
    def format_tool_history(self, tool_history):
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