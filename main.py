from utils.logger import agent_logger
from flow import create_flow, AgentState

def main():
    # 获取用户输入问题
    question = input("请输入你的问题：")
    if not question:
        agent_logger.warning("问题不能为空")
        return
    
    # 初始化状态
    initial_state = AgentState(
        question=question,
        search_result=None,
        answer=None,
        tools=None,
        selected_tool=None,
        tool_result=None
    )
    
    # 创建并运行工作流
    flow = create_flow()
    final_state = flow.invoke(initial_state)
    
    # 输出结果
    if final_state["search_result"]:
        agent_logger.info("\n【搜索结果】\n%s", final_state["search_result"])
    agent_logger.info("\n【答案】\n%s", final_state["answer"])

if __name__ == "__main__":
    main() 