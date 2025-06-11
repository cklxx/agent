# SPDX-License-Identifier: MIT

"""
Inspiration Agent module for handling creative writing and inspiration generation tasks.
"""

import logging
from typing import List, Any, Dict

from langgraph.prebuilt import create_react_agent
from src.llms.llm import get_llm_by_type
from src.prompts.template import apply_prompt_template # Assuming this is the correct path

# Setup logger
inspiration_agent_logger = logging.getLogger(__name__) # Changed from "inspiration_agent_logger" to __name__ for standard practice


def create_inspiration_agent(tools: List[Any]) -> Any:
    """
    Creates a ReAct-style agent specialized for creative writing and inspiration generation.

    This agent uses a reasoning LLM and is configured with specific prompts and tools
    suited for tasks like brainstorming ideas, developing characters, outlining plots,
    and generating creative text.

    Args:
        tools: A list of tools that the Inspiration Agent can use. These tools
               are expected to be relevant to creative writing, such as generating
               character elements, plot outlines, saving content, etc.

    Returns:
        An instance of a LangGraph ReAct agent configured for inspiration tasks.

    Raises:
        Exception: If any error occurs during the agent creation process.
    """
    inspiration_agent_logger.info(f"Creating Inspiration Agent with {len(tools)} tools.")

    # Log the names of the tools being used for easier debugging
    tool_names = [getattr(tool, "name", str(tool)) for tool in tools]
    inspiration_agent_logger.debug(f"Available tools for Inspiration Agent: {', '.join(tool_names)}")

    try:
        # Select the LLM for the agent's core logic
        # "reasoning" LLMs are typically better for ReAct-style agents that need to plan and use tools.
        llm = get_llm_by_type("reasoning")
        llm_model_name = getattr(llm, 'model_name', 'unknown_model')
        inspiration_agent_logger.info(f"Using LLM model for Inspiration Agent: {llm_model_name}")

        # Create the ReAct agent
        # The prompt is dynamically constructed using `apply_prompt_template` with the
        # "writing/inspiration_agent_react_prompt" template. This allows the agent's
        # behavior to be easily customized through the prompt file.
        agent = create_react_agent(
            name="inspiration_agent",  # Specific name for this agent
            model=llm,
            tools=tools,
            prompt=lambda state: apply_prompt_template("writing/inspiration_agent_react_prompt", state)
        )

        inspiration_agent_logger.info("Inspiration Agent created successfully.")
        return agent

    except Exception as e:
        inspiration_agent_logger.error(f"Failed to create Inspiration Agent: {str(e)}", exc_info=True)
        # Re-raise the exception to allow higher-level error handling if necessary
        raise


if __name__ == '__main__':
    # This is an example of how to quickly test the agent creation.
    # For this to run, you would need:
    # 1. Your LLM environment configured (e.g., API keys).
    # 2. The `src.prompts` and `src.llms` modules to be accessible.
    # 3. A list of mock or real tools.

    logging.basicConfig(level=logging.DEBUG)
    inspiration_agent_logger.info("--- Test: Attempting to create Inspiration Agent ---")

    # Mock tools for testing purposes
    from langchain_core.tools import tool

    @tool
    def mock_generate_ideas(query: str) -> str:
        """Generates mock creative ideas based on a query."""
        return f"Mock idea for '{query}': A talking cat solves mysteries in space."

    @tool
    def mock_save_to_file(content: str, filename: str) -> str:
        """Mocks saving content to a file."""
        return f"Mocked: Content '{content[:20]}...' saved to '{filename}'."

    test_tools = [mock_generate_ideas, mock_save_to_file]

    try:
        inspiration_agent_instance = create_inspiration_agent(tools=test_tools)
        inspiration_agent_logger.info(f"Test: Inspiration Agent instance created: {type(inspiration_agent_instance)}")

        # Example of how one might try to invoke it (actual invocation depends on LangGraph agent specifics)
        # This is a conceptual test and might need adjustment based on the agent's expected input structure.
        # test_input = {
        #     "messages": [("user", "Generate a story idea about a lonely robot.")],
        #     "locale": "en-US" # Example, as the prompt uses it
        # }
        # try:
        #     # result = inspiration_agent_instance.invoke(test_input)
        #     # inspiration_agent_logger.info(f"Test: Agent invocation result (conceptual): {result}")
        #     inspiration_agent_logger.info("Conceptual invocation test skipped as it requires full LangGraph setup.")
        # except Exception as invoke_err:
        #     inspiration_agent_logger.error(f"Test: Error invoking agent (conceptual): {invoke_err}", exc_info=True)

    except Exception as main_err:
        inspiration_agent_logger.error(f"Test: Failed to create Inspiration Agent in __main__: {main_err}", exc_info=True)

    inspiration_agent_logger.info("--- Test: Finished ---")
```
