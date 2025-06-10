# SPDX-License-Identifier: MIT

"""
Context管理器实现
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

from .base import BaseContext, ContextType, Priority, ContextProcessor
from .memory import WorkingMemory, LongTermMemory

logger = logging.getLogger(__name__)


class ContextManager:
    """Context管理器"""

    def __init__(
        self,
        working_memory_limit: int = 50,
        auto_compress: bool = True,
        compression_threshold: int = 100,
    ):
        """
        初始化Context管理器

        Args:
            working_memory_limit: 工作记忆容量限制
            auto_compress: 是否自动压缩
            compression_threshold: 压缩阈值
        """
        self.working_memory = WorkingMemory(limit=working_memory_limit)
        self.long_term_memory = LongTermMemory()

        self.auto_compress = auto_compress
        self.compression_threshold = compression_threshold

        # Context处理器
        self.processors: List[ContextProcessor] = []

        # 统计信息
        self.stats = {
            "total_contexts": 0,
            "active_contexts": 0,
            "compressed_contexts": 0,
            "retrievals": 0,
        }

        logger.info("ContextManager初始化完成")

    async def add_context(
        self,
        content: Union[str, Dict[str, Any]],
        context_type: ContextType = ContextType.CONVERSATION,
        metadata: Optional[Dict[str, Any]] = None,
        priority: Priority = Priority.MEDIUM,
        tags: Optional[List[str]] = None,
        parent_id: Optional[str] = None,
    ) -> str:
        """
        添加新的context

        Args:
            content: 内容
            context_type: context类型
            metadata: 元数据
            priority: 优先级
            tags: 标签
            parent_id: 父context ID

        Returns:
            context ID
        """
        context = BaseContext(
            content=content,
            context_type=context_type,
            metadata=metadata or {},
            priority=priority,
            tags=tags or [],
            parent_id=parent_id,
        )

        # 添加到工作记忆
        await self.working_memory.add(context)

        # 更新统计
        self.stats["total_contexts"] += 1
        self.stats["active_contexts"] += 1

        logger.debug(f"添加context: {context.id}, 类型: {context_type.value}")
        return context.id

    async def get_context(self, context_id: str) -> Optional[BaseContext]:
        """获取指定的context"""
        context = await self.working_memory.get(context_id)
        if context:
            context.update_access()
            self.stats["retrievals"] += 1
        return context

    async def search_contexts(
        self,
        query: str,
        context_type: Optional[ContextType] = None,
        tags: Optional[List[str]] = None,
        priority_filter: Optional[Priority] = None,
        limit: int = 10,
    ) -> List[BaseContext]:
        """
        搜索contexts

        Args:
            query: 查询关键词
            context_type: context类型过滤
            tags: 标签过滤
            priority_filter: 优先级过滤
            limit: 结果限制

        Returns:
            匹配的context列表
        """
        # 从工作记忆搜索
        results = await self.working_memory.search(query, limit)

        # 应用过滤器
        if context_type:
            results = [c for c in results if c.context_type == context_type]

        if tags:
            tag_set = set(tags)
            results = [c for c in results if tag_set.intersection(set(c.tags))]

        if priority_filter:
            results = [c for c in results if c.priority.value >= priority_filter.value]

        # 更新访问信息
        for context in results:
            context.update_access()

        self.stats["retrievals"] += len(results)
        return results[:limit]

    async def get_recent_contexts(
        self, context_type: Optional[ContextType] = None, limit: int = 10
    ) -> List[BaseContext]:
        """获取最近的contexts"""
        all_contexts = await self.working_memory.get_all()

        # 过滤类型
        if context_type:
            all_contexts = [c for c in all_contexts if c.context_type == context_type]

        # 按时间排序
        all_contexts.sort(key=lambda x: x.last_access, reverse=True)

        return all_contexts[:limit]

    async def get_related_contexts(
        self, context_id: str, limit: int = 5
    ) -> List[BaseContext]:
        """获取相关的contexts"""
        base_context = await self.get_context(context_id)
        if not base_context:
            return []

        # 获取所有contexts
        all_contexts = await self.working_memory.get_all()

        # 计算相关性
        related_contexts = []
        for context in all_contexts:
            if context.id == context_id:
                continue

            # 检查显式关联
            if (
                context.id in base_context.related_ids
                or base_context.id in context.related_ids
                or context.parent_id == context_id
                or base_context.parent_id == context.id
            ):
                related_contexts.append((1.0, context))
                continue

            # 简单的相关性计算
            similarity = self._calculate_similarity(base_context, context)
            if similarity > 0.3:  # 阈值过滤
                related_contexts.append((similarity, context))

        # 按相关性排序
        related_contexts.sort(key=lambda x: x[0], reverse=True)

        return [context for _, context in related_contexts[:limit]]

    def _calculate_similarity(
        self, context1: BaseContext, context2: BaseContext
    ) -> float:
        """计算两个context之间的相似性"""
        similarity = 0.0

        # 类型匹配
        if context1.context_type == context2.context_type:
            similarity += 0.3

        # 标签重叠
        tags1 = set(context1.tags)
        tags2 = set(context2.tags)
        if tags1 and tags2:
            tag_overlap = len(tags1.intersection(tags2)) / len(tags1.union(tags2))
            similarity += tag_overlap * 0.4

        # 内容相似性（简单实现）
        content1 = str(context1.content).lower()
        content2 = str(context2.content).lower()
        common_words = len(set(content1.split()).intersection(set(content2.split())))
        if common_words > 0:
            similarity += min(common_words / 10.0, 0.3)

        return similarity

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self.stats,
            "working_memory_size": self.working_memory.size(),
            "working_memory_limit": self.working_memory.limit,
        }
