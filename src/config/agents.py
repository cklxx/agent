# SPDX-License-Identifier: MIT

from typing import Literal

# Define available LLM types
LLMType = Literal["basic", "reasoning", "vision"]

# Define agent-LLM mapping
AGENT_LLM_MAP: dict[str, LLMType] = {
    "coordinator": "vision",
    "planner": "basic",
    "researcher": "basic",
    "coder": "reasoning",
    "reporter": "reasoning",
    "podcast_script_writer": "reasoning",
    "ppt_composer": "reasoning",
    "prose_writer": "reasoning",
}
