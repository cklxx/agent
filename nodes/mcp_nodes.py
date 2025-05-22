from pocketflow import Node
from utils.call_llm import call_llm
from utils.mcp_utils import get_tools, call_tool
import yaml
from typing import Dict, Any, Optional, List
import logging
import json

class GetToolsNode(Node):
    """Initialize and get tools"""
    def prep(self, shared: Dict) -> Optional[str]:
        """Prepare input for exec (e.g., the question)"""
        return shared.get("question", None)

    def exec(self, question: Optional[str]):
        """Retrieve tools from the MCP servers or local dummy"""
        logging.info(f"🔍 [GetToolsNode.exec] Calling get_tools...")
        try:
            # get_tools now returns a list of {'tool': tool_obj, 'server_name': server_name}
            tools_with_server_info = get_tools()
            logging.info(f"🔍 [GetToolsNode.exec] Received {len(tools_with_server_info)} tools with server info.")
            return tools_with_server_info
        except Exception as e:
            logging.error(f"❌ [GetToolsNode.exec] Error calling get_tools: {e}")
            return [] # Return empty list to allow flow to continue

    def post(self, shared: Dict, prep_res: Optional[str], exec_res: object) -> str:
        """Store tools and process to decision node"""
        logging.info(f"🔍 [GetToolsNode.post] Processing results...")
        tools_with_server_info = exec_res
        shared["tools_with_server_info"] = tools_with_server_info # Store the list with server info

        # Create a mapping from tool_name to (tool_object, server_name) for easier lookup
        tool_map = {}
        tool_info_for_prompt = []
        if tools_with_server_info:
            for item in tools_with_server_info:
                tool = item['tool']
                server_name = item['server_name']

                # Ensure tool has expected attributes/keys from the returned object/dict
                # Assuming tools are DictObject or similar structure with get or attribute access
                name = getattr(tool, 'name', tool.get('name', 'Unknown Tool'))
                description = getattr(tool, 'description', tool.get('description', 'No description'))
                input_schema = getattr(tool, 'inputSchema', tool.get('inputSchema', {}))

                # Store in map: tool_name -> (tool_object, server_name)
                tool_map[name] = (tool, server_name)

                properties = input_schema.get('properties', {})
                required = input_schema.get('required', [])

                params = []
                for param_name, param_info in properties.items():
                    param_type = param_info.get('type', 'unknown')
                    req_status = "(Required)" if param_name in required else "(Optional)"
                    params.append(f"    - {param_name} ({param_type}): {req_status}")

                # Format tool info for the prompt, include server name hint
                tool_info_for_prompt.append(f"[{server_name}.{name}]\n  Description: {description}\n  Parameters:\n" + "\n".join(params))

        shared["tool_map"] = tool_map # Store the tool map
        shared["tool_info_for_prompt"] = "\n".join(tool_info_for_prompt) # Store formatted info for prompt

        logging.info(f"🔍 [GetToolsNode.post] Created tool map and formatted info for prompt. Returning 'decide'.")
        return "decide"

class DecideToolNode(Node):
    def prep(self, shared: Dict):
        """Prepare the prompt for LLM to process the question"""
        # Use the formatted tool info including server name hint
        tool_info = shared.get("tool_info_for_prompt", "No tools available.")
        question = shared.get("question", "")
        thought = shared.get("thought", "")

        prompt = f"""
### CONTEXT
You are an assistant that can use tools via Model Context Protocol (MCP).

### ACTION SPACE
{tool_info}

### TASK
Answer this question: "{question}" and think about it step by step: "{thought}"

## NEXT ACTION
Analyze the question, extract any numbers or parameters, and decide which tool to use.
When selecting a tool, use the format 'server_name.tool_name'.
Return your response in this format:

```yaml
thinking: |
    <your step-by-step reasoning about what the question is asking and what numbers to extract>
tool: <server_name.tool_name> # Explicitly guide LLM to include server_name
reason: <why you chose this tool>
parameters:
    <parameter_name>: <parameter_value>
    <parameter_name>: <parameter_value>
```
IMPORTANT: 
1. Extract numbers from the question properly
2. Use proper indentation (4 spaces) for multi-line fields
3. Use the | character for multi-line text fields
4. When selecting a tool, use the format 'server_name.tool_name'.
"""
        return prompt

    def exec(self, prompt: str):
        """Call LLM to process the question and decide which tool to use"""
        logging.info("🤔 [DecideToolNode.exec] Calling LLM with prompt...")
        messages = [{"role": "user", "content": prompt + " /think"}]
        response = call_llm(messages)
        logging.info(f"🤔 [DecideToolNode.exec] Received LLM response: {response[:200]}...") # Print snippet of response
        return response

    def post(self, shared: Dict, prep_res: str, exec_res: str) -> str:
        """Extract decision from YAML and save to shared context"""
        logging.info(f"🤔 [DecideToolNode.post] Processing LLM response...")
        try:
            # Find the YAML block within the response
            yaml_start = exec_res.find("```yaml")
            yaml_end = exec_res.find("```", yaml_start + 1)

            if yaml_start != -1 and yaml_end != -1:
                 yaml_str = exec_res[yaml_start + len("```yaml"):yaml_end].strip()
            else:
                 # If no yaml block found, try to parse the whole response as yaml
                 yaml_str = exec_res.strip()

            decision = yaml.safe_load(yaml_str)

            selected_tool_full_name = decision.get("tool")
            shared["thinking"] = decision.get("thinking", "")
            shared["parameters"] = decision.get("parameters", {})

            if selected_tool_full_name and '.' in selected_tool_full_name:
                server_name, tool_name = selected_tool_full_name.split('.', 1)
                # 如果已经有多步思考结果，不再执行 sequentialthinking 工具
                if tool_name == "sequentialthinking" and shared.get("thought"):
                    logging.info("[DecideToolNode.post] 已有多步思考结果，跳过 sequentialthinking 工具执行。")
                    return "done"
                shared["server_name"] = server_name
                shared["tool_name"] = tool_name
                logging.info(f"💡 [DecideToolNode.post] Selected tool: {server_name}.{tool_name}")
                logging.info(f"🔢 [DecideToolNode.post] Extracted parameters: {shared['parameters']}")
                return "execute"
            else:
                logging.warning(f"🤷 [DecideToolNode.post] LLM did not select a tool in the expected format (server_name.tool_name): {selected_tool_full_name}")
                shared["tool_name"] = None # Ensure tool_name is None if format is wrong
                shared["server_name"] = None # Ensure server_name is None if format is wrong
                shared["answer"] = shared.get("thinking", "LLM unable to determine next step or tool.")
                return "done"

        except Exception as e:
            logging.error(f"❌ [DecideToolNode.post] Error parsing LLM response: {e}")
            logging.error("Raw response:", exec_res)
            shared["answer"] = f"Error processing tool decision: {e}"
            shared["tool_name"] = None # Ensure tool_name is None on error
            shared["server_name"] = None # Ensure server_name is None on error
            return "done"

class ExecuteToolNode(Node):
    def prep(self, shared: Dict) -> tuple:
        """Prepare tool execution parameters"""
        tool_name = shared.get("tool_name")
        server_name = shared.get("server_name") # Get server_name from shared
        parameters = shared.get("parameters", {})

        if not tool_name or not server_name:
            logging.warning("🔧 [ExecuteToolNode.prep] No tool name or server name provided for execution.")
            return (None, None, None) # Return None for all expected exec inputs

        logging.info(f"🔧 [ExecuteToolNode.prep] Preparing to execute tool '{tool_name}' on server '{server_name}' with parameters: {parameters}")
        return (server_name, tool_name, parameters) # Pass server_name to exec

    def exec(self, inputs: tuple):
        """Execute the chosen tool"""
        server_name, tool_name, parameters = inputs # Receive server_name here
        if not tool_name or not server_name:
            return "Error: No tool or server specified."

        logging.info(f"🔧 [ExecuteToolNode.exec] Executing tool '{tool_name}' on server '{server_name}' with parameters: {parameters}")
        # call_tool function signature should now match: call_tool(server_name, tool_name, parameters)
        result = call_tool(server_name, tool_name, parameters) # Pass server_name to call_tool
        return result

    def post(self, shared: Dict, prep_res: tuple, exec_res: Any) -> str:
        """Store tool execution result and finish"""
        logging.info(f"✅ [ExecuteToolNode.post] Tool execution finished.")
        shared["tool_execution_result"] = exec_res
        shared["tool_result"] = f"Tool {shared.get('server_name','local')}.{shared.get('tool_name','unknown')} executed. Result: {exec_res}"
        logging.info(f"\n✅ Tool Execution Result: {exec_res}")
        # 特殊处理 sequentialthinking 工具
        if shared.get("tool_name") == "sequentialthinking":
            # 假设 exec_res 返回 dict，包含 thoughtNumber, totalThoughts, branches, nextThoughtNeeded, thoughtHistoryLength
            # 兼容 exec_res 可能是 str 的情况
            if isinstance(exec_res, dict):
                shared["thoughtNumber"] = exec_res.get("thoughtNumber", 1)
                shared["totalThoughts"] = exec_res.get("totalThoughts", 3)
                shared["branches"] = exec_res.get("branches", [])
                shared["nextThoughtNeeded"] = exec_res.get("nextThoughtNeeded", True)
                shared["thoughtHistoryLength"] = exec_res.get("thoughtHistoryLength", len(exec_res.get("branches", [])))
            else:
                # 如果不是 dict，初始化默认参数
                shared["thoughtNumber"] = 1
                shared["totalThoughts"] = 3
                shared["branches"] = []
                shared["nextThoughtNeeded"] = True
                shared["thoughtHistoryLength"] = 0
            return "thinking"
        return "default"