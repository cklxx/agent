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
    # Leader agent (new unified agent)
    "architect": "reasoning",
    "leader": "reasoning",
    # Execute agent for analysis tasks
    "execute": "reasoning",
    # SWE (Software Engineering) agents
    "swe_architect": "reasoning",
    "swe_analyzer": "reasoning",
    "swe_engineer": "reasoning",
}
