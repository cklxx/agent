from pocketflow import Flow
from nodes.search_answer_nodes import AnswerNode
from nodes.mcp_nodes import GetToolsNode, DecideToolNode, ExecuteToolNode

def create_flow():
    # Original nodes
    answer_node = AnswerNode()

    # MCP nodes
    get_tools_node = GetToolsNode()
    decide_node = DecideToolNode()
    execute_tool_node = ExecuteToolNode()
   
    # MCP path: Get Tools -> Decide Tool -> Execute Tool
    get_tools_node - "decide" >> decide_node
    decide_node - "decide" >> decide_node
    decide_node - "done" >> answer_node
    # Decide the starting node - for now, let's start with getting tools for MCP demo
    return Flow(start=get_tools_node) 