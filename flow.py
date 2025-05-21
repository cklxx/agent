from pocketflow import Flow
from nodes.search_answer_nodes import SearchNode, AnswerNode, ThinkingNode
from nodes.mcp_nodes import GetToolsNode, DecideToolNode, ExecuteToolNode

def create_flow():
    # Original nodes
    answer_node = AnswerNode()

    # MCP nodes
    get_tools_node = GetToolsNode()
    decide_node = DecideToolNode()
    execute_tool_node = ExecuteToolNode()
    thinking_node = ThinkingNode()

    # Define flow paths
    # Original path: Search -> Answer
    # search_node >> answer_node # Keep this commented for now, or integrate later

    # MCP path: Get Tools -> Decide Tool -> Execute Tool
    get_tools_node - "decide" >> decide_node
    decide_node - "execute" >> execute_tool_node
    decide_node - "done" >> answer_node
    execute_tool_node - "thinking" >> thinking_node
    execute_tool_node - "default" >> answer_node
    thinking_node - "continue" >> thinking_node
    thinking_node - "default" >> decide_node
    # Decide the starting node - for now, let's start with getting tools for MCP demo
    return Flow(start=get_tools_node) 