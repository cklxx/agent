from agent.utils.logger import agent_logger
from agent.flow import create_flow, AgentState

def main():
    # Get user input question
    question = input("Please enter your question: ")
    if not question:
        agent_logger.warning("Question cannot be empty")
        return
    
    # Initialize state
    initial_state = AgentState(
        question=question,
        search_result=None,
        answer=None,
        tools=None,
        selected_tool=None,
        tool_result=None
    )
    
    # Create and run workflow
    flow = create_flow()
    final_state = flow.invoke(initial_state)
    
    # Output results
    if final_state["search_result"]:
        agent_logger.info("\n[Search Results]\n%s", final_state["search_result"])
    agent_logger.info("\n[Answer]\n%s", final_state["answer"])

if __name__ == "__main__":
    main() 