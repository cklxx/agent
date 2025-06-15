# SPDX-License-Identifier: MIT

"""
Thinking tool for logging thought processes.
Inspired by the tau-bench think tool.
"""

import logging
from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
def think(thought: str) -> str:
    """
    This is a no-op tool that logs a thought. It is inspired by the tau-bench think tool.
    Use the tool to think about something. It will not obtain new information or make any changes
    to the repository, but just log the thought. Use it when complex reasoning or brainstorming is needed.

    Common use cases:
    1. When exploring a repository and discovering the source of a bug, call this tool to brainstorm
       several unique ways of fixing the bug, and assess which change(s) are likely to be simplest and most effective
    2. After receiving test results, use this tool to brainstorm ways to fix failing tests
    3. When planning a complex refactoring, use this tool to outline different approaches and their tradeoffs
    4. When designing a new feature, use this tool to think through architecture decisions and implementation details
    5. When debugging a complex issue, use this tool to organize your thoughts and hypotheses

    The tool simply logs your thought process for better transparency and does not execute any code or make changes.

    Args:
        thought: Your thoughts

    Returns:
        Confirmation that the thought has been logged
    """
    # Log the thought for debugging/analysis purposes
    logger.info(f"THINKING: {thought}")

    # Return confirmation
    return "Your thought has been logged."
