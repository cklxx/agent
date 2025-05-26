from pocketflow import Node
from utils.call_llm import call_llm, stream_llm
from utils.mcp_utils import get_tools, call_tool, load_prompt_template
from utils.config import config
import yaml
from typing import Dict, Any, Optional, List
import logging
import json
import os

def load_config():
    """Load configuration from conf.yaml"""
    try:
        with open("conf.yaml", "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logging.error(f"Error loading config: {e}")
        return {}

class GetToolsNode(Node):
    """Initialize and get tools"""
    def prep(self, shared: Dict) -> Optional[str]:
        """Prepare input (e.g., the question)"""
        return shared.get("question", None)

    def exec(self, question: Optional[str]):
        """Retrieve tools from MCP servers or local dummy"""
        logging.info(f"🔍 [GetToolsNode.exec] Calling get_tools...")
        try:
            # get_tools now returns a list of {'tool': tool_obj, 'server_name': server_name}
            tools_with_server_info = get_tools()
            logging.info(f"🔍 [GetToolsNode.exec] Received {len(tools_with_server_info)} tools with server info.")
            return tools_with_server_info
        except Exception as e:
            logging.error(f"❌ [GetToolsNode.exec] Error calling get_tools: {e}")
            return []  # Return empty list to allow flow to continue

    def post(self, shared: Dict, prep_res: Optional[str], exec_res: object) -> str:
        """Store tools and process to decision node"""
        logging.info(f"🔍 [GetToolsNode.post] Processing results...")
        tools_with_server_info = exec_res
        shared["tools_with_server_info"] = tools_with_server_info  # Store the list with server info

        # Create a mapping from tool_name to (tool_object, server_name) for easier lookup
        tool_map = {}
        tool_info_for_prompt = []
        if tools_with_server_info:
            for item in tools_with_server_info:
                tool = item['tool']
                server_name = item['server_name']

                # Ensure tool has expected attributes/keys
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
                tool_info_for_prompt.append(
                    f"[{server_name}.{name}]\n"
                    f"  Description: {description}\n"
                    f"  Parameters:\n" + "\n".join(params)
                )

        shared["tool_map"] = tool_map
        shared["tool_info_for_prompt"] = "\n".join(tool_info_for_prompt)  # Store formatted info for prompt

        logging.info(f"🔍 [GetToolsNode.post] Created tool map and formatted info for prompt. Returning 'decide'.")
        return "decide"

class DecideToolNode(Node):
    def prep(self, shared: Dict):
        """Prepare the prompt for LLM to process the question"""
        # Load prompt template
        prompt_template = load_prompt_template("decide_tool")
        if not prompt_template:
            logging.error("Failed to load prompt template")
            return ""

        # Use the formatted tool info including server name hint
        tool_info = shared.get("tool_info_for_prompt", "No tools available.")
        question = shared.get("question", "")
        thought = shared.get("thought", "")
        
        # Get previous tool call results
        previous_results = []
        if "tool_call_results" in shared:
            for i, result in enumerate(shared["tool_call_results"], 1):
                previous_results.append(f"Tool Call {i}:")
                previous_results.append(f"Result: {result}")
                previous_results.append("---")
        
        previous_results_text = "\n".join(previous_results) if previous_results else "No previous tool calls."

        # Format the prompt template
        prompt = prompt_template.format(
            tool_info=tool_info,
            question=question,
            thought=thought,
            previous_results=previous_results_text
        )
        return prompt

    def exec(self, prompt: str):
        """Call LLM to process the question and decide which tool to use"""
        logging.info("🤔 [DecideToolNode.exec] Calling LLM with prompt...")
        
        # 使用配置管理模块获取模型类型
        model_type = config.get_model_type()
        
        # 根据模型类型添加相应的思考模式标记
        thinking_marker = " /think" if model_type == "qwen" else " :thinking"
        messages = [{"role": "user", "content": prompt + thinking_marker}]
        
        response_stream = stream_llm(messages)
        
        # 收集流式输出的内容
        full_response = ""
        for chunk in response_stream:
            full_response += chunk
            print(chunk, end="", flush=True)
        print()  # 添加换行
        
        logging.info(f"🤔 [DecideToolNode.exec] Completed LLM response")
        return full_response

    def post(self, shared: Dict, prep_res: str, exec_res: str) -> str:
        """Process LLM response and execute tool calls"""
        try:
            # Initialize or increment tool call count
            tool_call_count = shared.get("tool_call_count", 0)
            tool_call_count += 1
            shared["tool_call_count"] = tool_call_count
            
            # Check if we've reached the maximum number of tool calls
            if tool_call_count >= 5:
                print("\n⚠️ 已达到最大工具调用次数限制 (5次)")
                shared["tool_execution_result"] = json.dumps(shared["tool_call_results"], ensure_ascii=False, indent=3)
                return "done"
            
            # Extract YAML content from the response
            yaml_content = exec_res
            if "```yaml" in exec_res:
                # Extract content between ```yaml and ```
                yaml_start = exec_res.find("```yaml") + len("```yaml")
                yaml_end = exec_res.find("```", yaml_start)
                if yaml_end != -1:
                    yaml_content = exec_res[yaml_start:yaml_end].strip()
                else:
                    shared["tool_execution_result"] = "Error: Invalid YAML block format"
                    return "done"
            elif "```" in exec_res:
                # Handle case where language is not specified
                yaml_start = exec_res.find("```") + len("```")
                yaml_end = exec_res.find("```", yaml_start)
                if yaml_end != -1:
                    yaml_content = exec_res[yaml_start:yaml_end].strip()
                else:
                    shared["tool_execution_result"] = "Error: Invalid code block format"
                    return "done"
            
            # Parse YAML content
            try:
                response_data = yaml.safe_load(yaml_content)
            except yaml.YAMLError as e:
                logging.error(f"YAML parsing error: {str(e)}")
                shared["tool_execution_result"] = f"Error: Invalid YAML format - {str(e)}"
                return "done"
            
            # Check required fields
            if not isinstance(response_data, dict):
                shared["tool_execution_result"] = "Error: Invalid response format - expected a dictionary"
                return "done"
                
            thinking = response_data.get('thinking', '')
            actions = response_data.get('actions', [])
            need_more_tools = response_data.get('need_more_tools', False)
            reason = response_data.get('reason', '')
            
            if not thinking or not actions:
                shared["tool_execution_result"] = "Error: Missing required fields (thinking or actions)"
                return "done"
            
            # Print thinking process
            print("\nThinking Process:")
            print(thinking)
            print("\nExecution Plan:")
            print(f"当前工具调用次数: {tool_call_count}/5")
            
            # Store all tool call results
            results = []
            
            # Execute each tool call
            for i, action in enumerate(actions, 1):
                tool = action.get('tool')
                reason = action.get('reason', '')
                parameters = action.get('parameters', {})
                
                if not tool:
                    results.append(f"Error: Action {i} missing tool name")
                    continue
                
                # Print current tool call info
                print(f"\n[{i}] Using tool: {tool}")
                print(f"Reason: {reason}")
                print(f"Parameters: {parameters}")
                
                try:
                    # Parse server name and tool name
                    if '.' not in tool:
                        raise ValueError(f"Invalid tool name format: {tool}")
                    server_name, tool_name = tool.split('.')
                    
                    # Call tool
                    result = call_tool(server_name, tool_name, parameters)
                    results.append(result)
                    
                    # Print tool call result
                    print(f"Result: {result}")
                    
                except Exception as e:
                    error_msg = f"Tool call failed: {str(e)}"
                    results.append(error_msg)
                    print(f"Error: {error_msg}")
            
            # Store tool call results in shared dictionary
            if "tool_call_results" not in shared:
                shared["tool_call_results"] = []
            shared["tool_call_results"].extend(results)
            
            # Print whether more tools are needed
            print(f"\nNeed more tools: {need_more_tools}")
            print(f"Reason: {reason}")
            
            # Return next step based on need_more_tools and tool call count
            if need_more_tools and tool_call_count < 5:
                return "decide"
            else:
                if need_more_tools:
                    print("\n⚠️ 已达到最大工具调用次数限制，无法继续使用工具")
                # Store result in shared dictionary
                shared["tool_execution_result"] = json.dumps(shared["tool_call_results"], ensure_ascii=False, indent=3)
                return "done"
            
        except Exception as e:
            error_msg = f"Error processing response: {str(e)}"
            logging.error(error_msg)
            shared["tool_execution_result"] = error_msg
            return "done"

class ExecuteToolNode(Node):
    def prep(self, shared: Dict) -> tuple:
        """Prepare tool execution parameters"""
        tool_name = shared.get("tool_name")
        server_name = shared.get("server_name")
        parameters = shared.get("parameters", {})

        if not tool_name or not server_name:
            logging.warning("🔧 [ExecuteToolNode.prep] No tool name or server name provided.")
            return (None, None, None)

        logging.info(f"🔧 [ExecuteToolNode.prep] Preparing to execute tool '{tool_name}' on server '{server_name}' with parameters: {parameters}")
        return (server_name, tool_name, parameters)

    def exec(self, server_name: str, tool_name: str, parameters: Dict):
        """Execute tool call"""
        logging.info(f"🔧 [ExecuteToolNode.exec] Executing tool '{tool_name}' on server '{server_name}'")
        try:
            result = call_tool(server_name, tool_name, parameters)
            logging.info(f"✅ [ExecuteToolNode.exec] Tool execution successful")
            return result
        except Exception as e:
            error_msg = f"Tool execution failed: {str(e)}"
            logging.error(f"❌ [ExecuteToolNode.exec] {error_msg}")
            return error_msg

    def post(self, shared: Dict, prep_res: tuple, exec_res: str) -> str:
        """Process tool execution result"""
        logging.info(f"🔧 [ExecuteToolNode.post] Processing tool execution result")
        
        # If execution failed, return error message
        if isinstance(exec_res, str) and exec_res.startswith("Error"):
            shared["answer"] = exec_res
            return "done"
            
        # Store execution result
        shared["tool_result"] = exec_res
        
        # If this is the last tool call, return done
        if shared.get("is_last_tool", False):
            shared["answer"] = exec_res
            return "done"
            
        # Otherwise continue with next tool
        return "decide"