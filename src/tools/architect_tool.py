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
ARCHITECT_SYSTEM_PROMPT = """You are an expert software architect. Create clear, actionable implementation plans.

**Process:**
1. **Analyze** - Core functionality, constraints, requirements
2. **Design** - Technologies, patterns, architecture 
3. **Plan** - Sequential implementation steps

**Output Requirements:**
- Specific, actionable steps for junior engineers
- Include file structure, configuration, testing
- No code implementation, just clear instructions
- Focus on what to build, not how to code it

**Format:**
```
## Analysis
[Brief problem analysis]

## Technical Approach  
[Technologies and patterns]

## Implementation Steps
1. [Specific step with files/configs]
2. [Next step with validation]
...
```

Be concise. Be specific. Be actionable."""


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
    Deploy intelligent agent for code analysis and exploration.

    Args:
        prompt: Task for agent to perform
        environment_info: Environment details
        workspace: Workspace directory

    Returns:
        Agent analysis and findings
    """
    try:
        logger.info(f"🤖 Dispatching agent: {prompt[:50]}...")

        # Create agent with read-only tools
        tools = [
            "view_file",
            "list_files",
            "glob_search",
            "grep_search",
            "think",
            "notebook_read",
        ]
        agent = create_agent(
            name="dispatch_agent",
            tools=tools,
            llm_type=AGENT_LLM_MAP["researcher"],
            prompt_template="dispatch_agent",
        )

        # Prepare state for prompt template
        state = {
            "messages": [HumanMessage(content=prompt)],
            "workspace": workspace or "",
            "environment_info": environment_info or "",
            "task_description": prompt,
            "locale": "zh-CN",
        }

        result = agent.invoke(state)

        # Extract response
        if isinstance(result, dict) and "messages" in result:
            response = result["messages"][-1].content
        else:
            response = str(result)

        logger.info("✅ Agent dispatch completed")
        return response

    except Exception as e:
        logger.error(f"❌ dispatch_agent error: {e}")
        return f"Error: {str(e)}"
