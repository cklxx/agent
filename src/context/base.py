# SPDX-License-Identifier: MIT

"""
Agent Context基础类定义
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4


class ContextType(Enum):
    """Context类型枚举"""

    CONVERSATION = "conversation"  # 对话上下文
    TASK = "task"  # 任务上下文
    KNOWLEDGE = "knowledge"  # 知识上下文
    SYSTEM = "system"  # 系统上下文
    CODE = "code"  # 代码上下文
    FILE = "file"  # 文件上下文
    EXECUTION = "execution"  # 执行上下文
    EXECUTION_RESULT = "execution_result"  # 执行结果上下文
    PLANNING = "planning"  # 规划上下文
    TASK_RESULT = "task_result"  # 任务结果上下文
    RAG = "rag"  # RAG检索上下文
    RAG_CODE = "rag_code"  # RAG代码检索上下文
    RAG_SEMANTIC = "rag_semantic"  # RAG语义检索上下文


class Priority(Enum):
    """优先级枚举"""

    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class BaseContext:
    """基础Context数据结构"""

    id: str = field(default_factory=lambda: str(uuid4()))
    context_type: ContextType = ContextType.CONVERSATION
    content: Union[str, Dict[str, Any]] = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    priority: Priority = Priority.MEDIUM
    tags: List[str] = field(default_factory=list)

    # 关联信息
    parent_id: Optional[str] = None
    related_ids: List[str] = field(default_factory=list)

    # 状态信息
    is_active: bool = True
    is_compressed: bool = False
    access_count: int = 0
    last_access: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "context_type": self.context_type.value,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
            "priority": self.priority.value,
            "tags": self.tags,
            "parent_id": self.parent_id,
            "related_ids": self.related_ids,
            "is_active": self.is_active,
            "is_compressed": self.is_compressed,
            "access_count": self.access_count,
            "last_access": self.last_access.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseContext":
        """从字典创建Context对象"""
        context = cls(
            id=data.get("id", str(uuid4())),
            context_type=ContextType(
                data.get("context_type", ContextType.CONVERSATION.value)
            ),
            content=data.get("content", ""),
            metadata=data.get("metadata", {}),
            timestamp=datetime.fromisoformat(
                data.get("timestamp", datetime.now().isoformat())
            ),
            priority=Priority(data.get("priority", Priority.MEDIUM.value)),
            tags=data.get("tags", []),
            parent_id=data.get("parent_id"),
            related_ids=data.get("related_ids", []),
            is_active=data.get("is_active", True),
            is_compressed=data.get("is_compressed", False),
            access_count=data.get("access_count", 0),
            last_access=datetime.fromisoformat(
                data.get("last_access", datetime.now().isoformat())
            ),
        )
        return context

    def update_access(self):
        """更新访问信息"""
        self.access_count += 1
        self.last_access = datetime.now()


class ContextStorage(ABC):
    """Context存储接口"""

    @abstractmethod
    async def save(self, context: BaseContext) -> bool:
        """保存context"""
        pass

    @abstractmethod
    async def load(self, context_id: str) -> Optional[BaseContext]:
        """加载context"""
        pass

    @abstractmethod
    async def delete(self, context_id: str) -> bool:
        """删除context"""
        pass

    @abstractmethod
    async def search(
        self, query: str, context_type: Optional[ContextType] = None, limit: int = 10
    ) -> List[BaseContext]:
        """搜索context"""
        pass

    @abstractmethod
    async def list_by_type(
        self, context_type: ContextType, limit: int = 10
    ) -> List[BaseContext]:
        """按类型列出context"""
        pass


class ContextProcessor(ABC):
    """Context处理器接口"""

    @abstractmethod
    async def process(self, context: BaseContext) -> BaseContext:
        """处理context"""
        pass

    @abstractmethod
    def can_process(self, context: BaseContext) -> bool:
        """判断是否可以处理该context"""
        pass
