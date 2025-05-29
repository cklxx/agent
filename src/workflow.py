# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import asyncio
import logging
from src.graph import build_graph

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Default level is INFO
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


def enable_debug_logging():
    """Enable debug level logging for more detailed execution information."""
    # 启用详细的调试日志
    logging.getLogger("src").setLevel(logging.DEBUG)
    
    # 启用HTTP请求日志
    logging.getLogger("httpx").setLevel(logging.DEBUG)
    logging.getLogger("openai").setLevel(logging.DEBUG)
    logging.getLogger("requests").setLevel(logging.DEBUG)
    
    # 启用langchain相关日志
    logging.getLogger("langchain").setLevel(logging.DEBUG)
    logging.getLogger("langgraph").setLevel(logging.DEBUG)


def enable_api_debug_logging():
    """Enable even more detailed API logging for debugging."""
    # 非常详细的HTTP日志
    import httpx
    import requests
    
    # 启用requests的详细日志
    logging.getLogger("urllib3.connectionpool").setLevel(logging.DEBUG)
    
    # 自定义httpx日志
    class HTTPXLogger:
        def __init__(self):
            self.logger = logging.getLogger("httpx_detailed")
            self.logger.setLevel(logging.DEBUG)
        
        def log_request(self, request):
            self.logger.debug(f"REQUEST: {request.method} {request.url}")
            self.logger.debug(f"REQUEST Headers: {dict(request.headers)}")
            if request.content:
                self.logger.debug(f"REQUEST Body: {request.content}")
        
        def log_response(self, response):
            self.logger.debug(f"RESPONSE: {response.status_code}")
            self.logger.debug(f"RESPONSE Headers: {dict(response.headers)}")
            self.logger.debug(f"RESPONSE Content: {response.text}")


logger = logging.getLogger(__name__)

# Create the graph
graph = build_graph()


async def run_agent_workflow_async(
    user_input: str,
    debug: bool = False,
    max_plan_iterations: int = 1,
    max_step_num: int = 3,
    enable_background_investigation: bool = True,
):
    """Run the agent workflow asynchronously with the given user input.

    Args:
        user_input: The user's query or request
        debug: If True, enables debug level logging
        max_plan_iterations: Maximum number of plan iterations
        max_step_num: Maximum number of steps in a plan
        enable_background_investigation: If True, performs web search before planning to enhance context

    Returns:
        The final state after the workflow completes
    """
    if not user_input:
        raise ValueError("Input could not be empty")

    if debug:
        enable_debug_logging()
        enable_api_debug_logging()
        logger.debug("Debug logging enabled with detailed API logging")

    logger.info(f"Starting async workflow with user input: {user_input}")
    initial_state = {
        # Runtime Variables
        "messages": [{"role": "user", "content": user_input}],
        "auto_accepted_plan": True,
        "enable_background_investigation": enable_background_investigation,
    }
    config = {
        "configurable": {
            "thread_id": "default",
            "max_plan_iterations": max_plan_iterations,
            "max_step_num": max_step_num,
            "mcp_settings": {
                "servers": {
                    "mcp-github-trending": {
                        "transport": "stdio",
                        "command": "uvx",
                        "args": ["mcp-github-trending"],
                        "enabled_tools": ["get_github_trending_repositories"],
                        "add_to_agents": ["researcher"],
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

    logger.info("Async workflow completed successfully")


if __name__ == "__main__":
    print(graph.get_graph(xray=True).draw_mermaid())
