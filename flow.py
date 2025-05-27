from typing import TypedDict, Annotated, Sequence
from langgraph.graph import StateGraph, END
from nodes.search_answer_nodes import AnswerNode
from nodes.mcp import GetToolsNode, DecideToolNode, ExecuteToolNode

class AgentState(TypedDict):
    question: str
    search_result: str | None
    answer: str | None
    tools: list | None  # 完整的工具列表，包含所有 MCP 调用信息
    tool_info_for_prompt: str | None  # 用于提示的工具描述
    selected_tools: list | None  # 选中的工具列表
    tool_results: list | None  # 工具执行结果列表（累积）
    tool_history: list | None  # 工具执行历史记录
    thinking: str | None
    need_more_tools: bool | None  # 是否需要更多工具
    tool_call_count: int | None  # 工具调用次数

def create_flow():
    # 创建工作流图
    workflow = StateGraph(AgentState)
    
    # 创建节点
    get_tools_node = GetToolsNode()
    decide_node = DecideToolNode()
    execute_tool_node = ExecuteToolNode()
    answer_node = AnswerNode()
    
    # 添加节点到工作流
    workflow.add_node("get_tools", get_tools_node)
    workflow.add_node("decide_tool", decide_node)
    workflow.add_node("execute_tool", execute_tool_node)
    workflow.add_node("answer_node", answer_node)
    
    # 定义边和条件
    workflow.add_edge("get_tools", "decide_tool")
    workflow.add_conditional_edges(
        "decide_tool",
        lambda x: "execute_tool" if x.get("selected_tools") else "answer_node",
        {
            "execute_tool": "execute_tool",
            "answer_node": "answer_node"
        }
    )
    workflow.add_conditional_edges(
        "execute_tool",
        lambda x: "decide_tool" if x.get("need_more_tools", False) else "answer_node",
        {
            "decide_tool": "decide_tool",
            "answer_node": "answer_node"
        }
    )
    workflow.add_edge("answer_node", END)
    
    # 设置入口节点
    workflow.set_entry_point("get_tools")
    
    return workflow.compile() 