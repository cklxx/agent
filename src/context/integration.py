# SPDX-License-Identifier: MIT

"""
Context模块与Agent系统集成
"""

from typing import Dict, Any, Optional
from .manager import ContextManager
from .base import ContextType, Priority


class AgentContextIntegration:
    """Agent系统的Context集成类"""

    def __init__(self, context_manager: ContextManager):
        self.context_manager = context_manager

    async def enhance_agent_prompt(self, base_prompt: str, query: str = None) -> str:
        """使用context增强Agent prompt"""
        if not query:
            recent_contexts = await self.context_manager.get_recent_contexts(limit=3)
        else:
            recent_contexts = await self.context_manager.search_contexts(query, limit=3)

        if not recent_contexts:
            return base_prompt

        context_info = "\n## 相关上下文信息:\n"
        for i, context in enumerate(recent_contexts, 1):
            content_preview = str(context.content)[:100]
            context_info += f"{i}. {context.context_type.value}: {content_preview}...\n"

        return f"{base_prompt}\n{context_info}\n请结合以上上下文信息来回答。"


class CodeAgentContextProcessor:
    """Code Agent专用的Context处理器"""

    def __init__(self, context_manager: ContextManager):
        self.context_manager = context_manager

    async def process_code_task(
        self, task_description: str, working_directory: str = None
    ) -> Dict[str, Any]:
        """处理代码任务"""
        task_context_id = await self.context_manager.add_context(
            content=task_description,
            context_type=ContextType.TASK,
            priority=Priority.HIGH,
            tags=["code_task", "planning"],
            metadata={"working_directory": working_directory},
        )

        related_tasks = await self.context_manager.search_contexts(
            query=task_description, context_type=ContextType.TASK, limit=3
        )

        return {
            "task_context_id": task_context_id,
            "related_tasks": [c.to_dict() for c in related_tasks],
            "suggestions": [f"发现 {len(related_tasks)} 个相似的历史任务"],
        }
