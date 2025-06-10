# SPDX-License-Identifier: MIT

"""
Context检索器实现
"""

from typing import List, Optional
from .base import BaseContext, ContextType, Priority
from .memory import WorkingMemory, LongTermMemory


class ContextRetriever:
    """Context检索器"""

    def __init__(self, working_memory: WorkingMemory, long_term_memory: LongTermMemory):
        self.working_memory = working_memory
        self.long_term_memory = long_term_memory

    async def get_by_id(self, context_id: str) -> Optional[BaseContext]:
        """通过ID获取context"""
        return await self.working_memory.get(context_id)

    async def search(self, query: str, limit: int = 10) -> List[BaseContext]:
        """搜索contexts"""
        return await self.working_memory.search(query, limit)
