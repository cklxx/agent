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
