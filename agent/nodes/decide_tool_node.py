from .base_node import BaseNode
from agent.utils.mcp_utils import get_tools, load_prompt_template, parse_yaml_response
from agent.utils.call_llm import stream_llm
from agent.utils.logger import mcp_logger

class DecideToolNode(BaseNode):
    """Decide which tools to use"""
    def __call__(self, state: dict) -> dict:
        mcp_logger.info(f"🔍 [DecideToolNode] Starting to decide which tools to use...")
        mcp_logger.debug(f"🔍 [DecideToolNode] Current state: {state}")
        
        # Check if tool call limit has been reached
        if self.check_tool_call_limit(state):
            return state
        
        # Load prompt template
        prompt_template = load_prompt_template("decide_tool")
        if not prompt_template:
            mcp_logger.error("Failed to load prompt template")
            return state
        
        # Prepare prompt
        tool_info = state.get("tool_info_for_prompt", "No tools available.")
        question = state.get("question", "")
        thought = state.get("thinking", "")
        
        # Get tool execution history
        tool_history = state.get("tool_history", [])
        tool_history_text = self.format_tool_history(tool_history)
        
        # Format prompt
        prompt = prompt_template.format(
            tool_info=tool_info,
            question=question,
            thought=thought,
            tool_history=tool_history_text
        )
        
        # Add system prompt to ensure correct format
        system_prompt = """You are a tool calling assistant. You must strictly respond in the following YAML format:

```yaml
thinking: |
    <your thinking process>
actions:
    - tool: <server_name.tool_name>
      reason: <reason for using this tool>
      parameters:
          <parameter_name>: <parameter_value>
```

Important notes:
1. You must use YAML format
2. You must include thinking and actions fields
3. If no tools are needed, actions can be an empty list
4. Each tool call must include tool, reason, and parameters fields
"""
        
        # Call LLM
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        try:
            # Collect streaming output
            full_response = ""
            for chunk in stream_llm(messages, task_type="standard_tool_calls"):
                full_response += chunk
                print(chunk, end="", flush=True)
            print()
            
            # Parse YAML response
            response_data = parse_yaml_response(full_response)
            mcp_logger.debug(f"Parsed YAML data: {response_data}")
            
            # Update state
            state["thinking"] = response_data.get("thinking", "")
            
            # Process tool selection
            actions = response_data.get("actions", [])
            selected_tools = []
            
            # Ensure actions is a list
            if not isinstance(actions, list):
                mcp_logger.error(f"actions is not a list type: {type(actions)}")
                actions = []
            
            for action in actions:
                if isinstance(action, dict):
                    tool_name = action.get("tool", "")
                    if not tool_name:
                        mcp_logger.warning(f"Tool name is empty: {action}")
                        continue
                        
                    # Handle server_name.tool_name format
                    if "." in tool_name:
                        tool_name = tool_name.split(".")[-1]
                    
                    # Validate if tool exists
                    tools = get_tools()
                    if not any(t["name"] == tool_name for t in tools):
                        mcp_logger.warning(f"Tool does not exist: {tool_name}")
                        continue
                    
                    selected_tools.append({
                        "name": tool_name,
                        "parameters": action.get("parameters", {}),
                        "reason": action.get("reason", "")
                    })
            
            state["selected_tools"] = selected_tools
            mcp_logger.info(f"Selected tools: {selected_tools}")
            
            mcp_logger.debug(f"🔍 [DecideToolNode] Updated state: {state}")
            return state
            
        except Exception as e:
            mcp_logger.error(f"❌ [DecideToolNode] Error processing response: {e}")
            state["selected_tools"] = []
            return state 