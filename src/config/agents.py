# SPDX-License-Identifier: MIT

from typing import Literal

# Define available LLM types
LLMType = Literal["basic", "reasoning", "vision"]

# Define agent-LLM mapping
AGENT_LLM_MAP: dict[str, LLMType] = {
    "coordinator": "reasoning",
    "planner": "basic",
    "researcher": "basic",
    "coder": "reasoning",
    "reporter": "reasoning",
    "podcast_script_writer": "reasoning",
    "ppt_composer": "reasoning",
    "prose_writer": "reasoning",
    # Code-specific agents
    "code_researcher": "basic",
    "code_coder": "reasoning",
    # Architect agent (new unified agent)
    "architect": "reasoning",
}
