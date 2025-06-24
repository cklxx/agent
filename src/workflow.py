# SPDX-License-Identifier: MIT

import asyncio
import logging
from src.graph.builder import build_graph
from src.config.logging_config import setup_simplified_logging, setup_debug_logging

# 日志配置函数已迁移到 src/config/logging_config.py


logger = logging.getLogger(__name__)

# Create the unified research agent graph
graph = build_graph()


async def run_research_agent_async(
    user_input: str,
    debug: bool = False,
    max_research_iterations: int = 3,
    enable_background_investigation: bool = True,
    auto_execute: bool = True,
    locale: str = "en-US",
):
    """Run the unified research agent asynchronously.

    Args:
        user_input: The research query or objective
        debug: If True, enables debug level logging
        max_research_iterations: Maximum number of research iterations
        enable_background_investigation: If True, performs background investigation before planning
        auto_execute: If True, automatically executes the research plan without human feedback
        locale: Language locale for the research

    Returns:
        The final state after the research completes
    """
    if not user_input:
        raise ValueError("Research input cannot be empty")

    if debug:
        setup_debug_logging()
        logger.debug("Debug logging enabled for research agent")
    else:
        setup_simplified_logging()

    logger.info(f"🔬 Starting research agent with objective: {user_input}")

    initial_state = {
        "messages": [{"role": "user", "content": user_input}],
        "locale": locale,
        "enable_background_investigation": enable_background_investigation,
        "auto_execute": auto_execute,
        "max_research_iterations": max_research_iterations,
        "research_findings": [],
        "current_step_index": 0,
    }

    config = {
        "configurable": {
            "thread_id": "research_session",
            "max_search_results": 10,
            "mcp_settings": {
                "servers": {
                    "mcp-github-trending": {
                        "transport": "stdio",
                        "command": "uvx",
                        "args": ["mcp-github-trending"],
                        "enabled_tools": ["get_github_trending_repositories"],
                        "add_to_agents": ["research_agent"],
                    }
                }
            },
        },
        "recursion_limit": 100,
    }
    last_message_cnt = 0
    async for s in graph.astream(
        input=initial_state, config=config, stream_mode="values"
    ):
        try:
            if isinstance(s, dict) and "messages" in s:
                if len(s["messages"]) <= last_message_cnt:
                    continue
                last_message_cnt = len(s["messages"])
                message = s["messages"][-1]
                if isinstance(message, tuple):
                    print(message)
                else:
                    message.pretty_print()
            else:
                # For any other output format
                print(f"Output: {s}")
        except Exception as e:
            logger.error(f"Error processing stream output: {e}")
            print(f"Error processing output: {str(e)}")

    logger.info("🎉 Research agent workflow completed successfully")


# Backwards compatibility alias
async def run_agent_workflow_async(*args, **kwargs):
    """Legacy function name for backwards compatibility."""
    return await run_research_agent_async(*args, **kwargs)


if __name__ == "__main__":
    print(graph.get_graph(xray=True).draw_mermaid())
