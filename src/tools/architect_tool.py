# SPDX-License-Identifier: MIT

"""
Architecture planning tool.
Uses project's LLM infrastructure to analyze technical requirements and generate implementation plans.
Enhanced to support agent-based execution with tools.
"""

import logging
from typing import Optional
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage

from src.prompts.template import apply_prompt_template
from src.agents.agents import create_agent
from src.config.agents import AGENT_LLM_MAP
from src.llms.llm import get_llm_by_type

logger = logging.getLogger(__name__)

# Enhanced system prompt for the architect with recursive capability
ARCHITECT_SYSTEM_PROMPT = """You are an expert software architect. Your role is to analyze technical requirements and produce clear, actionable implementation plans.

These plans will then be carried out by a junior software engineer so you need to be specific and detailed. However do not actually write the code, just explain the plan.

Follow these steps for each request:

1. **Carefully analyze requirements** to identify core functionality and constraints
   - Understand the problem domain and technical context
   - Identify key functional and non-functional requirements
   - Note any constraints, dependencies, or limitations

2. **Define clear technical approach** with specific technologies and patterns
   - Choose appropriate technologies, frameworks, and tools
   - Specify architectural patterns and design principles
   - Consider scalability, performance, and maintainability

3. **Break down implementation** into concrete, actionable steps at the appropriate level of abstraction
   - Create sequential steps that a junior engineer can follow
   - Be specific about what needs to be done in each step
   - Include file structure, configuration, and integration points
   - Specify testing and validation checkpoints

Keep responses focused, specific and actionable.

IMPORTANT: Do not ask the user if you should implement the changes at the end. Just provide the plan as described above.
IMPORTANT: Do not attempt to write the code or use any string modification tools. Just provide the plan."""


@tool
def architect_plan(prompt: str, context: Optional[str] = None) -> str:
    """
    Create detailed technical implementation plans and architecture designs.

    Args:
        prompt: Technical problem or coding task description
        context: Optional additional context information

    Returns:
        Detailed implementation plan with actionable steps
    """
    try:
        logger.info(f"🏗️ Creating architect plan for: {prompt}")

        # Prepare the complete prompt with context
        full_prompt = prompt
        if context:
            full_prompt = f"{prompt}\n\nAdditional Context:\n{context}"

        # Use the project's LLM infrastructure
        llm = get_llm_by_type(AGENT_LLM_MAP["architect"])

        # Create the message with system prompt and user request
        messages = [
            {"role": "system", "content": ARCHITECT_SYSTEM_PROMPT},
            {"role": "user", "content": full_prompt},
        ]

        # Get the architect's plan
        response = llm.invoke(messages)

        if hasattr(response, "content"):
            plan = response.content
        else:
            plan = str(response)

        logger.info("✅ Architect plan generated successfully")
        return plan

    except Exception as e:
        logger.error(f"❌ Error in architect_plan: {str(e)}")
        return f"Error generating architect plan: {str(e)}"


@tool
def dispatch_agent(
    prompt: str, environment_info: Optional[str] = None, workspace: Optional[str] = None
) -> str:
    """
    Deploy intelligent agent for code exploration, analysis, and modifications.

    Args:
        prompt: Specific task for the agent to perform
        environment_info: Optional environment details
        workspace: Optional workspace directory path

    Returns:
        Agent's analysis, findings, and improvements made
    """
    try:
        logger.info(f"🤖 Dispatching agent for: {prompt}")

        # Read-only tools for safe exploration
        tools = [
            "view_file",
            "list_files",
            "glob_search",
            "grep_search",
            "think",
            "notebook_read",
        ]

        # Create agent with read-only tools
        agent = create_agent(
            name="dispatch_agent", tools=tools, llm_type=AGENT_LLM_MAP["researcher"]
        )

        # Prepare state with environment information
        state = {
            "messages": [HumanMessage(content=prompt)],
            "workspace": workspace,
            "environment_info": environment_info,
            "locale": "zh-CN",
        }

        # Execute the agent
        result = agent.invoke(state)

        # Extract the agent's response
        if isinstance(result, dict) and "messages" in result:
            last_message = result["messages"][-1]
            if hasattr(last_message, "content"):
                response = last_message.content
            else:
                response = str(last_message)
        else:
            response = str(result)

        logger.info("✅ Agent dispatch completed successfully")
        return response

    except Exception as e:
        logger.error(f"❌ Error in dispatch_agent: {str(e)}")
        return f"Error dispatching agent: {str(e)}"
