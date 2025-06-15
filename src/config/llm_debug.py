# SPDX-License-Identifier: MIT

"""
LLM Debug module - provides debugging capabilities for LLM calls
"""

import logging

logger = logging.getLogger(__name__)


class LLMDebugger:
    """Simple LLM debugger for tracking agent steps and LLM calls"""

    def __init__(self):
        self.debug_enabled = True

    def log_agent_step(
        self, agent_name: str, step_title: str, step_description: str = ""
    ):
        """Log agent execution step"""
        if self.debug_enabled:
            logger.debug(f"[{agent_name}] {step_title}: {step_description}")

    def log_llm_call(
        self,
        agent_name: str,
        messages: list,
        model_type: str = "unknown",
        extra_context: dict = None,
    ):
        """Log LLM call details"""
        if self.debug_enabled:
            logger.debug(
                f"[{agent_name}] LLM调用 (模型: {model_type}, 消息数: {len(messages)})"
            )
            if extra_context:
                logger.debug(f"[{agent_name}] 额外上下文: {extra_context}")

    def log_llm_response(
        self, agent_name: str, response: any, duration_ms: float = None
    ):
        """Log LLM response details"""
        if self.debug_enabled:
            duration_info = f", 耗时: {duration_ms:.2f}ms" if duration_ms else ""
            response_preview = (
                str(response)[:100] + "..."
                if len(str(response)) > 100
                else str(response)
            )
            logger.debug(f"[{agent_name}] LLM响应: {response_preview}{duration_info}")

    def log_tool_call(self, tool_name: str, args: dict = None, result: str = None):
        """Log tool call details"""
        if self.debug_enabled:
            if args:
                logger.debug(f"[工具调用] {tool_name}: {args}")
            if result:
                logger.debug(f"[工具结果] {tool_name}: {result}")


# Global debugger instance
_debugger = LLMDebugger()


def get_llm_debugger() -> LLMDebugger:
    """Get the global LLM debugger instance"""
    return _debugger
