# SPDX-License-Identifier: MIT

import logging

from langchain.schema import HumanMessage

from src.config.agents import AGENT_LLM_MAP
from src.llms.llm import get_llm_by_type
from src.prose.graph.state import ProseState
from src.prompts import apply_prompt_template

logger = logging.getLogger(__name__)


def prose_improve_node(state: ProseState):
    logger.info("Generating prose improve content...")
    model = get_llm_by_type(AGENT_LLM_MAP["prose_writer"])

    # 构建状态用于apply_prompt_template
    prompt_state = {
        "messages": [HumanMessage(content=f"The existing text is: {state['content']}")],
        "content": state["content"],
    }

    # 使用apply_prompt_template统一管理prompt
    messages = apply_prompt_template("prose/prose_improver", prompt_state)
    prose_content = model.invoke(messages)

    logger.info(f"prose_content: {prose_content}")
    return {"output": prose_content.content}
