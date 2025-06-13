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
    Advanced architecture planning tool that analyzes technical requirements and creates detailed implementation plans.

    This tool excels at:
    - Breaking down complex technical problems into manageable steps
    - Designing system architectures and choosing appropriate technologies
    - Creating actionable implementation roadmaps
    - Recommending tools and approaches for each phase
    - Planning for testing, validation, and deployment

    Use this tool when you need to:
    - Plan how to implement a new feature or system
    - Design technical solutions for complex problems
    - Break down large tasks into smaller, executable steps
    - Choose appropriate technologies and tools
    - Create comprehensive implementation strategies

    Args:
        prompt: The technical request, problem description, or coding task to analyze
        context: Optional context from previous planning sessions, current system state, or related information

    Returns:
        Detailed implementation plan with specific, actionable steps and tool recommendations
    """
    try:
        # Use project's LLM infrastructure
        llm = get_llm_by_type(AGENT_LLM_MAP["architect"])

        # Prepare the full prompt with enhanced context
        if context:
            full_prompt = f"""## Context Information
{context}

## Technical Request
{prompt}

Please provide a detailed implementation plan following the three-step approach outlined in your instructions."""
        else:
            full_prompt = f"""## Technical Request
{prompt}

Please provide a detailed implementation plan following the three-step approach outlined in your instructions."""

        # Create messages for direct LLM invocation
        messages = [
            {"role": "system", "content": ARCHITECT_SYSTEM_PROMPT},
            {"role": "user", "content": full_prompt},
        ]

        # Generate response using project's LLM
        try:
            response = llm.invoke(messages)
            plan = response.content.strip()

            # Return clean, focused plan
            logger.info(f"Generated architecture plan for: {prompt[:100]}...")
            return plan

        except Exception as e:
            logger.error(f"LLM API call failed: {e}")
            return f"Error: Failed to generate plan. LLM API error: {str(e)}"

    except Exception as e:
        logger.error(f"Architect tool error: {e}")
        return f"Error: Failed to generate architecture plan: {str(e)}"


@tool
def dispatch_agent(
    prompt: str, environment_info: Optional[str] = None, workspace: Optional[str] = None
) -> str:
    """
    Launch a new agent that has comprehensive tools for exploration, analysis, and intelligent modifications.

    This tool creates an intelligent agent with access to:
    - view_file: Read file contents (supports images and text files)
    - list_files: List directory contents with detailed information
    - glob_search: Find files using glob patterns
    - grep_search: Search file contents using regex patterns
    - think: Log thoughts and reasoning processes
    - notebook_read: Read Jupyter notebook contents
    - edit_file: Create new files or modify existing files
    - replace_file: Replace specific content in files
    - bash_command: Execute shell commands for testing and validation

    Use this tool when you need to:
    - Search for keywords or files with uncertain matches
    - Explore codebases and understand project structures
    - Gather information from multiple sources
    - Perform analysis that requires multiple investigation steps
    - Make targeted improvements to code or documentation
    - Validate changes with testing commands

    Args:
        prompt: The task for the agent to perform - be specific about what information you need
        environment_info: Optional environment information (Python version, platform, etc.)
        workspace: Optional workspace directory path

    Returns:
        The agent's comprehensive analysis, findings, and any improvements made
    """
    try:
        # Import available tools for the dispatch agent
        from src.tools import (
            view_file,
            list_files,
            glob_search,
            grep_search,
            think,
            bash_command,
            replace_file,
            edit_file,
        )

        # Define available tools for the dispatch agent (read-only tools)
        available_tools = [
            view_file,
            list_files,
            glob_search,
            grep_search,
            think,
            bash_command,
            replace_file,
            edit_file,
        ]

        # Create agent using project's infrastructure
        agent = create_agent(
            agent_name="dispatch_agent",
            agent_type="dispatch_agent",  # Use dispatch_agent LLM configuration
            tools=available_tools,
            prompt_template="dispatch_agent",
        )
        
        # Create proper initial state for the agent
        initial_state = {
            "messages": [HumanMessage(content=prompt)],
            "task_description": prompt,
        }

        # Add environment information if provided
        if environment_info:
            initial_state["environment_info"] = environment_info

        # Add workspace information if provided
        if workspace:
            initial_state["workspace"] = workspace

        try:
            # Execute the agent with the initial state
            result = agent.invoke(input=initial_state, config={"recursion_limit": 20})
            
            # Extract the final response
            if hasattr(result, 'messages') and result.messages:
                final_message = result.messages[-1]
                if hasattr(final_message, 'content'):
                    response_content = final_message.content
                else:
                    response_content = str(final_message)
            else:
                response_content = str(result)

            # Format the result
            formatted_result = f"# Dispatch Agent Report\n\n{response_content}\n\n---\n*Report generated by dispatch agent using project infrastructure*"

            logger.info(f"Dispatch agent completed task: {prompt[:100]}...")
            return formatted_result

        except Exception as e:
            logger.error(f"Dispatch agent execution failed: {e}")
            return f"Error: Dispatch agent failed to complete task. Agent execution error: {str(e)}"

    except Exception as e:
        logger.error(f"Dispatch agent tool error: {e}")
        return f"Error: Failed to launch dispatch agent: {str(e)}"
