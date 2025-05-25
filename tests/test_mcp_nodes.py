import unittest
from unittest.mock import patch, MagicMock
import logging
from nodes.mcp_nodes import GetToolsNode

class TestGetToolsNode(unittest.TestCase):

    def test_prep_method(self):
        node = GetToolsNode()

        # Scenario 1: question in shared
        shared_s1 = {"question": "What is the weather?"}
        self.assertEqual(node.prep(shared_s1), "What is the weather?")

        # Scenario 2: question not in shared
        shared_s2 = {}
        self.assertIsNone(node.prep(shared_s2)) # Default for .get if key not found is None

        # Scenario 3: question is None in shared
        shared_s3 = {"question": None}
        self.assertIsNone(node.prep(shared_s3))

    @patch('nodes.mcp_nodes.get_tools')
    def test_exec_method(self, mock_get_tools):
        node = GetToolsNode()

        # Scenario 1: get_tools returns valid tool data
        tool_data_s1 = [{
            "tool": {"name": "tool1", "description": "desc1", "inputSchema": {"properties": {"param1": {"type": "string"}}, "required": ["param1"]}},
            "server_name": "server1"
        }]
        mock_get_tools.return_value = tool_data_s1
        
        result_s1 = node.exec("some question")
        
        mock_get_tools.assert_called_once_with("some question")
        self.assertEqual(result_s1, tool_data_s1)

        mock_get_tools.reset_mock()

        # Scenario 2: get_tools returns an empty list
        mock_get_tools.return_value = []
        result_s2 = node.exec("some question")
        self.assertEqual(result_s2, [])
        mock_get_tools.assert_called_once_with("some question")

        mock_get_tools.reset_mock()

        # Scenario 3: get_tools raises an exception
        mock_get_tools.side_effect = Exception("API Error")
        with self.assertLogs(logger='nodes.mcp_nodes', level='ERROR') as cm:
            result_s3 = node.exec("some question")
        self.assertEqual(result_s3, [])
        self.assertIn("Error in GetToolsNode.exec: API Error", cm.output[0])
        mock_get_tools.assert_called_once_with("some question")

    def test_post_method(self):
        node = GetToolsNode()
        prep_res = "some question"

        # Scenario 1: exec_res is a list of valid tool data
        exec_res_s1 = [
            {"tool": {"name": "tool1", "description": "desc1", "inputSchema": {"properties": {"param1": {"type": "string", "description": "Param 1 desc"}}, "required": ["param1"]}}, "server_name": "server1"},
            {"tool": {"name": "tool2", "description": "desc2", "inputSchema": {"properties": {"param2": {"type": "integer"}}, "required": []}}, "server_name": "server2"} # param2 is optional
        ]
        shared_s1 = {}
        result_val_s1 = node.post(shared_s1, prep_res, exec_res_s1)

        self.assertEqual(shared_s1["tools_with_server_info"], exec_res_s1)
        expected_tool_map_s1 = {
            "tool1": (exec_res_s1[0]["tool"], "server1"),
            "tool2": (exec_res_s1[1]["tool"], "server2")
        }
        self.assertEqual(shared_s1["tool_map"], expected_tool_map_s1)
        
        expected_prompt_s1_lines = [
            "Server Name: server1",
            "Tool Name: tool1",
            "Tool Description: desc1",
            "Parameters:",
            "  param1 (string): Param 1 desc (Required)",
            "Server Name: server2",
            "Tool Name: tool2",
            "Tool Description: desc2",
            "Parameters:",
            "  param2 (integer): (Optional)" # No description for param2
        ]
        for line in expected_prompt_s1_lines:
            self.assertIn(line, shared_s1["tool_info_for_prompt"])
        self.assertEqual(result_val_s1, "decide")

        # Scenario 2: exec_res is an empty list
        exec_res_s2 = []
        shared_s2 = {}
        result_val_s2 = node.post(shared_s2, prep_res, exec_res_s2)

        self.assertEqual(shared_s2["tools_with_server_info"], [])
        self.assertEqual(shared_s2["tool_map"], {})
        self.assertEqual(shared_s2["tool_info_for_prompt"], "") # Current behavior is empty string
        self.assertEqual(result_val_s2, "decide")

        # Scenario 3: Tool data has missing fields
        exec_res_s3 = [
            {"tool": {"name": "tool_no_schema", "description": "desc_no_schema"}, "server_name": "server3"}, # No inputSchema
            {"tool": {"name": "tool_no_props", "description": "desc_no_props", "inputSchema": {}}, "server_name": "server4"}, # inputSchema but no properties
            {"tool": {"name": "tool_no_required", "description": "desc_no_req", "inputSchema": {"properties": {"p1": {"type": "string"}}}}, "server_name": "server5"} # No 'required' array
        ]
        shared_s3 = {}
        result_val_s3 = node.post(shared_s3, prep_res, exec_res_s3)

        self.assertEqual(shared_s3["tool_map"]["tool_no_schema"], (exec_res_s3[0]["tool"], "server3"))
        self.assertEqual(shared_s3["tool_map"]["tool_no_props"], (exec_res_s3[1]["tool"], "server4"))
        self.assertEqual(shared_s3["tool_map"]["tool_no_required"], (exec_res_s3[2]["tool"], "server5"))

        prompt_s3 = shared_s3["tool_info_for_prompt"]
        self.assertIn("Server Name: server3\nTool Name: tool_no_schema\nTool Description: desc_no_schema\nParameters:\n  No parameters available.", prompt_s3)
        self.assertIn("Server Name: server4\nTool Name: tool_no_props\nTool Description: desc_no_props\nParameters:\n  No parameters available.", prompt_s3)
        self.assertIn("Server Name: server5\nTool Name: tool_no_required\nTool Description: desc_no_req\nParameters:\n  p1 (string): (Optional)", prompt_s3) # p1 is optional by default if not in 'required'
        self.assertEqual(result_val_s3, "decide")

        # Scenario 4: Tool data uses dict access
        tool_dict_s4 = {"name": "dict_tool", "description": "dict_desc", "inputSchema": {"properties": {"p1": {"type": "int", "description": "Dict Param 1"}}, "required": []}}
        exec_res_s4 = [{"tool": tool_dict_s4, "server_name": "server_dict"}]
        shared_s4 = {}
        result_val_s4 = node.post(shared_s4, prep_res, exec_res_s4)

        self.assertEqual(shared_s4["tool_map"]["dict_tool"], (tool_dict_s4, "server_dict"))
        expected_prompt_s4_lines = [
            "Server Name: server_dict",
            "Tool Name: dict_tool",
            "Tool Description: dict_desc",
            "Parameters:",
            "  p1 (int): Dict Param 1 (Optional)"
        ]
        for line in expected_prompt_s4_lines:
            self.assertIn(line, shared_s4["tool_info_for_prompt"])
        self.assertEqual(result_val_s4, "decide")

if __name__ == '__main__':
    unittest.main()

# --- Tests for DecideToolNode ---
from nodes.mcp_nodes import DecideToolNode
import yaml

class TestDecideToolNode(unittest.TestCase):

    def test_prep_method(self):
        node = DecideToolNode()

        # Scenario 1: All data in shared
        shared_s1 = {"tool_info_for_prompt": "ToolA: ...", "question": "Use ToolA", "thought": "Thinking about ToolA"}
        prompt_s1 = node.prep(shared_s1)
        self.assertIn("【可选工具列表】\nToolA: ...", prompt_s1)
        self.assertIn("【用户问题】\nUse ToolA", prompt_s1)
        self.assertIn("【历史思考】\nThinking about ToolA", prompt_s1)

        # Scenario 2: Missing optional data in shared (no "thought")
        shared_s2 = {"tool_info_for_prompt": "ToolB: ...", "question": "Use ToolB"}
        prompt_s2 = node.prep(shared_s2)
        self.assertIn("【可选工具列表】\nToolB: ...", prompt_s2)
        self.assertIn("【用户问题】\nUse ToolB", prompt_s2)
        self.assertIn("【历史思考】\n无", prompt_s2) # Default when thought is missing

        # Scenario 3: Missing "tool_info_for_prompt"
        shared_s3 = {"question": "What can you do?"}
        prompt_s3 = node.prep(shared_s3)
        self.assertIn("【可选工具列表】\n无", prompt_s3) # Default when tool_info is missing
        self.assertIn("【用户问题】\nWhat can you do?", prompt_s3)
        self.assertIn("【历史思考】\n无", prompt_s3)


    @patch('nodes.mcp_nodes.call_llm')
    def test_exec_method(self, mock_call_llm):
        node = DecideToolNode()

        # Scenario 1: LLM returns valid YAML
        yaml_str_s1 = """
```yaml
thinking: |
    I need to use ToolA.
tool: server1.ToolA
reason: Because it's ToolA.
parameters:
    param1: value1
```
"""
        mock_call_llm.return_value = yaml_str_s1
        result_s1 = node.exec("prompt_from_prep_s1")
        
        mock_call_llm.assert_called_once()
        args, kwargs = mock_call_llm.call_args
        self.assertEqual(len(args[0]), 2) # messages list
        self.assertEqual(args[0][0]["role"], "system")
        self.assertEqual(args[0][1]["role"], "user")
        self.assertEqual(args[0][1]["content"], "prompt_from_prep_s1\n\n/think")
        self.assertEqual(result_s1, yaml_str_s1)

        mock_call_llm.reset_mock()

        # Scenario 2: LLM returns string without YAML block
        no_yaml_str_s2 = "Just some text, no YAML."
        mock_call_llm.return_value = no_yaml_str_s2
        result_s2 = node.exec("prompt_from_prep_s2")
        self.assertEqual(result_s2, no_yaml_str_s2)
        mock_call_llm.assert_called_once() # Ensure it was still called

        mock_call_llm.reset_mock()

        # Scenario 3: call_llm raises an exception
        mock_call_llm.side_effect = Exception("LLM Error")
        with self.assertRaises(Exception) as context:
            node.exec("prompt_from_prep_s3")
        self.assertTrue("LLM Error" in str(context.exception))
        mock_call_llm.assert_called_once()


    def test_post_method(self):
        node = DecideToolNode()
        prep_res = "some prompt" # Not used by post method itself

        # Scenario 1: Valid YAML decision for a tool
        exec_res_s1 = "```yaml\nthinking: I will use ToolX.\ntool: serverX.ToolX\nreason: test\nparameters:\n  p1: v1\n```"
        shared_s1 = {}
        result_val_s1 = node.post(shared_s1, prep_res, exec_res_s1)
        
        self.assertEqual(shared_s1["thinking"], "I will use ToolX.")
        self.assertEqual(shared_s1["server_name"], "serverX")
        self.assertEqual(shared_s1["tool_name"], "ToolX")
        self.assertEqual(shared_s1["parameters"], {"p1": "v1"})
        self.assertEqual(result_val_s1, "execute")

        # Scenario 2: YAML indicates no tool (tool is None)
        exec_res_s2 = "```yaml\nthinking: I don't need a tool.\ntool: None\nreason: done\nparameters: {}\n```"
        shared_s2 = {}
        result_val_s2 = node.post(shared_s2, prep_res, exec_res_s2)
        
        self.assertEqual(shared_s2["thinking"], "I don't need a tool.")
        self.assertIsNone(shared_s2.get("tool_name"))
        self.assertIsNone(shared_s2.get("server_name"))
        self.assertEqual(shared_s2.get("answer"), "I don't need a tool.") # answer gets thinking if no tool
        self.assertEqual(result_val_s2, "done")

        # Scenario 2b: YAML indicates no tool (tool is not server.tool format)
        exec_res_s2b = "```yaml\nthinking: I don't need a tool.\ntool: not_a_server_tool_format\nreason: done\nparameters: {}\n```"
        shared_s2b = {}
        with self.assertLogs(logger='nodes.mcp_nodes', level='WARNING') as cm_s2b:
            result_val_s2b = node.post(shared_s2b, prep_res, exec_res_s2b)
        
        self.assertEqual(shared_s2b["thinking"], "I don't need a tool.")
        self.assertIsNone(shared_s2b.get("tool_name"))
        self.assertIsNone(shared_s2b.get("server_name"))
        self.assertEqual(shared_s2b.get("answer"), "I don't need a tool.")
        self.assertEqual(result_val_s2b, "done")
        self.assertIn("Tool name 'not_a_server_tool_format' is not in 'server_name.tool_name' format.", cm_s2b.output[0])


        # Scenario 3: YAML is malformed or parsing error
        exec_res_s3 = "```yaml\nthinking: bad yaml\ntool: server.Tool\nparameters: p1: v1```" # malformed parameters
        shared_s3 = {}
        with self.assertLogs(logger='nodes.mcp_nodes', level='ERROR') as cm_s3:
            result_val_s3 = node.post(shared_s3, prep_res, exec_res_s3)
        
        self.assertIn("Error parsing LLM response YAML", cm_s3.output[0])
        self.assertIn("Error parsing LLM response", shared_s3["answer"])
        self.assertIsNone(shared_s3.get("tool_name"))
        self.assertEqual(result_val_s3, "done")

        # Scenario 4: LLM response without YAML block, directly parseable as YAML
        exec_res_s4 = "thinking: direct yaml\ntool: serverDirect.ToolY\nreason: direct\nparameters: {}\n"
        shared_s4 = {}
        result_val_s4 = node.post(shared_s4, prep_res, exec_res_s4)

        self.assertEqual(shared_s4["thinking"], "direct yaml")
        self.assertEqual(shared_s4["server_name"], "serverDirect")
        self.assertEqual(shared_s4["tool_name"], "ToolY")
        self.assertEqual(shared_s4["parameters"], {})
        self.assertEqual(result_val_s4, "execute")

        # Scenario 5: LLM response without YAML block, not parseable as YAML
        exec_res_s5 = "Just some text, no YAML block and not YAML itself."
        shared_s5 = {}
        with self.assertLogs(logger='nodes.mcp_nodes', level='ERROR') as cm_s5:
            result_val_s5 = node.post(shared_s5, prep_res, exec_res_s5)
        
        self.assertIn("Error parsing LLM response as YAML", cm_s5.output[0])
        self.assertIn("Error parsing LLM response", shared_s5["answer"])
        self.assertIsNone(shared_s5.get("tool_name"))
        self.assertEqual(result_val_s5, "done")

        # Scenario 6: Tool is 'sequentialthinking' and 'thought' already exists in shared
        exec_res_s6 = "```yaml\nthinking: I will use sequentialthinking.\ntool: someServer.sequentialthinking\nreason: test\nparameters: {}\n```"
        shared_s6 = {"thought": "previous thoughts exist"}
        with self.assertLogs(logger='nodes.mcp_nodes', level='INFO') as cm_s6:
            result_val_s6 = node.post(shared_s6, prep_res, exec_res_s6)
        
        self.assertEqual(shared_s6["thinking"], "I will use sequentialthinking.")
        self.assertEqual(shared_s6["server_name"], "someServer")
        self.assertEqual(shared_s6["tool_name"], "sequentialthinking")
        self.assertEqual(result_val_s6, "done") # Skipped execution
        self.assertIn("Sequential thinking tool 'someServer.sequentialthinking' selected, but 'thought' already exists in shared. Skipping execution.", cm_s6.output[0])
        # 'answer' should contain the thinking if execution is skipped this way
        self.assertEqual(shared_s6.get("answer"), "I will use sequentialthinking.")

# --- Tests for ExecuteToolNode ---
from nodes.mcp_nodes import ExecuteToolNode

class TestExecuteToolNode(unittest.TestCase):

    def test_prep_method(self):
        node = ExecuteToolNode()

        # Scenario 1: All data in shared
        shared_s1 = {"tool_name": "ToolA", "server_name": "server1", "parameters": {"p1": "v1"}}
        self.assertEqual(node.prep(shared_s1), ("server1", "ToolA", {"p1": "v1"}))

        # Scenario 2: Missing "parameters"
        shared_s2 = {"tool_name": "ToolB", "server_name": "server2"}
        self.assertEqual(node.prep(shared_s2), ("server2", "ToolB", {}))

        # Scenario 3: Missing "tool_name" or "server_name"
        with self.assertLogs(logger='nodes.mcp_nodes', level='WARNING') as cm_s3_tool:
            shared_s3_tool = {"server_name": "server1", "parameters": {}}
            self.assertEqual(node.prep(shared_s3_tool), (None, None, None))
        self.assertIn("Tool name or server name missing in shared data.", cm_s3_tool.output[0])

        with self.assertLogs(logger='nodes.mcp_nodes', level='WARNING') as cm_s3_server:
            shared_s3_server = {"tool_name": "ToolA", "parameters": {}}
            self.assertEqual(node.prep(shared_s3_server), (None, None, None))
        self.assertIn("Tool name or server name missing in shared data.", cm_s3_server.output[0])


    @patch('nodes.mcp_nodes.call_tool')
    def test_exec_method(self, mock_call_tool):
        node = ExecuteToolNode()

        # Scenario 1: Valid inputs, call_tool succeeds
        inputs_s1 = ("server1", "ToolA", {"p1": "v1"})
        mock_call_tool.return_value = "ToolA execution result"
        result_s1 = node.exec(inputs_s1)
        
        mock_call_tool.assert_called_once_with("server1", "ToolA", {"p1": "v1"})
        self.assertEqual(result_s1, "ToolA execution result")

        mock_call_tool.reset_mock()

        # Scenario 2: No tool_name or server_name in inputs
        inputs_s2_notool = (None, "ToolA", {})
        result_s2_notool = node.exec(inputs_s2_notool)
        self.assertEqual(result_s2_notool, "Error: No tool or server specified.")
        mock_call_tool.assert_not_called()

        inputs_s2_noserver = ("server1", None, {})
        result_s2_noserver = node.exec(inputs_s2_noserver)
        self.assertEqual(result_s2_noserver, "Error: No tool or server specified.")
        mock_call_tool.assert_not_called()

        # Scenario 3: call_tool raises an exception
        inputs_s3 = ("server1", "ToolA", {})
        mock_call_tool.side_effect = Exception("Tool Error")
        with self.assertRaises(Exception) as context:
            node.exec(inputs_s3)
        self.assertTrue("Tool Error" in str(context.exception))
        mock_call_tool.assert_called_once_with("server1", "ToolA", {})


    def test_post_method(self):
        node = ExecuteToolNode()
        prep_res = ("server1", "ToolA", {}) # Example, not directly used by post logic other than being passed

        # Scenario 1: Default tool execution
        shared_s1 = {"server_name": "server1", "tool_name": "ToolA"}
        exec_res_s1 = "ToolA output"
        result_val_s1 = node.post(shared_s1, prep_res, exec_res_s1)
        
        self.assertEqual(shared_s1["tool_execution_result"], "ToolA output")
        self.assertEqual(shared_s1["tool_result"], "Tool server1.ToolA executed. Result: ToolA output")
        self.assertEqual(result_val_s1, "default")

        # Scenario 2: Tool is "sequentialthinking"
        shared_s2 = {"server_name": "sThinkServer", "tool_name": "sequentialthinking"}
        exec_res_s2 = {"thoughtNumber": 2, "totalThoughts": 5, "branches": ["b1"], "nextThoughtNeeded": True, "thoughtHistoryLength": 1}
        result_val_s2 = node.post(shared_s2, prep_res, exec_res_s2)

        self.assertEqual(shared_s2["tool_execution_result"], exec_res_s2)
        expected_tool_result_s2 = f"Tool sThinkServer.sequentialthinking executed. Result: {str(exec_res_s2)}"
        self.assertEqual(shared_s2["tool_result"], expected_tool_result_s2)
        self.assertEqual(shared_s2["thoughtNumber"], 2)
        self.assertEqual(shared_s2["totalThoughts"], 5)
        self.assertEqual(shared_s2["branches"], ["b1"])
        self.assertTrue(shared_s2["nextThoughtNeeded"])
        self.assertEqual(shared_s2["thoughtHistoryLength"], 1)
        self.assertEqual(result_val_s2, "thinking")

        # Scenario 3: Tool is "sequentialthinking", but exec_res is not a dict
        shared_s3 = {"server_name": "sThinkServer", "tool_name": "sequentialthinking"}
        exec_res_s3 = "some string instead of dict"
        result_val_s3 = node.post(shared_s3, prep_res, exec_res_s3)

        self.assertEqual(shared_s3["tool_execution_result"], "some string instead of dict")
        expected_tool_result_s3 = f"Tool sThinkServer.sequentialthinking executed. Result: {exec_res_s3}"
        self.assertEqual(shared_s3["tool_result"], expected_tool_result_s3)
        # Check for default values
        self.assertEqual(shared_s3["thoughtNumber"], 1)
        self.assertEqual(shared_s3["totalThoughts"], 3)
        self.assertEqual(shared_s3["branches"], [])
        self.assertTrue(shared_s3["nextThoughtNeeded"])
        self.assertEqual(shared_s3["thoughtHistoryLength"], 0)
        self.assertEqual(result_val_s3, "thinking")

        # Scenario 4: Missing server_name or tool_name in shared for tool_result string
        shared_s4 = {} # Simulating missing server_name and tool_name
        exec_res_s4 = "Some output"
        result_val_s4 = node.post(shared_s4, prep_res, exec_res_s4)
        
        self.assertEqual(shared_s4["tool_execution_result"], "Some output")
        self.assertEqual(shared_s4["tool_result"], "Tool local.unknown executed. Result: Some output")
        self.assertEqual(result_val_s4, "default")
