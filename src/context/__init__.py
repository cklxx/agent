# SPDX-License-Identifier: MIT

"""
Agent通用Context管理模块

该模块提供agent系统的通用context管理能力，包括：
- 会话上下文管理
- 工作记忆管理
- 长期记忆存储
- 上下文检索和筛选
- 上下文压缩和摘要
"""

from .base import BaseContext, ContextType
from .manager import ContextManager
from .memory import WorkingMemory, LongTermMemory
from .retriever import ContextRetriever
from .compressor import ContextCompressor
from .code_rag_adapter import CodeRAGAdapter

__all__ = [
    "BaseContext",
    "ContextType",
    "ContextManager",
    "WorkingMemory",
    "LongTermMemory",
    "ContextRetriever",
    "ContextCompressor",
    "CodeRAGAdapter",
]
