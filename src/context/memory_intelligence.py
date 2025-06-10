"""
智能记忆管理模块
利用LLM生成长期记忆，智能判断是否存入RAG知识库、压缩、索引
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum

from ..llms.llm import get_llm_by_type
from .base import BaseContext, ContextType, Priority
from .memory import LongTermMemory
from .manager import ContextManager

logger = logging.getLogger(__name__)


class MemoryImportance(Enum):
    """记忆重要性等级"""

    CRITICAL = 5  # 关键信息，必须保存
    HIGH = 4  # 高价值信息
    MEDIUM = 3  # 中等价值信息
    LOW = 2  # 低价值信息
    TRIVIAL = 1  # 琐碎信息，可忽略


@dataclass
class MemoryAnalysis:
    """记忆分析结果"""

    importance: MemoryImportance
    should_save_to_rag: bool
    summary: str
    key_concepts: List[str]
    reasoning: str
    relevance_score: float


class IntelligentMemoryManager:
    """智能记忆管理器"""

    def __init__(
        self,
        llm_client=None,
        importance_threshold: MemoryImportance = MemoryImportance.MEDIUM,
        rag_threshold: float = 0.7,
        max_context_length: int = 4000,
    ):
        """
        初始化智能记忆管理器

        Args:
            llm_client: LLM客户端
            importance_threshold: 记忆重要性阈值
            rag_threshold: RAG存储阈值
            max_context_length: 最大上下文长度
        """
        self.llm_client = llm_client or get_llm_by_type("basic")
        self.importance_threshold = importance_threshold
        self.rag_threshold = rag_threshold
        self.max_context_length = max_context_length
        self.long_term_memory = LongTermMemory()

        # 统计信息
        self.stats = {
            "analyzed_contexts": 0,
            "saved_to_long_term": 0,
            "saved_to_rag": 0,
            "compressed_contexts": 0,
            "rejected_contexts": 0,
        }

        logger.info("IntelligentMemoryManager初始化完成")

    async def analyze_context_batch(
        self, contexts: List[BaseContext]
    ) -> List[MemoryAnalysis]:
        """
        批量分析上下文的记忆价值

        Args:
            contexts: 要分析的上下文列表

        Returns:
            分析结果列表
        """
        if not contexts:
            return []

        # 构建分析prompt
        context_summaries = []
        for i, ctx in enumerate(contexts):
            content_preview = (
                str(ctx.content)[:200] + "..."
                if len(str(ctx.content)) > 200
                else str(ctx.content)
            )
            context_summaries.append(
                {
                    "index": i,
                    "type": ctx.context_type.value,
                    "content": content_preview,
                    "metadata": ctx.metadata,
                    "tags": ctx.tags,
                }
            )

        prompt = self._build_analysis_prompt(context_summaries)

        try:
            response = await self.llm_client.ainvoke(prompt)

            # 解析分析结果
            analyses = self._parse_analysis_response(response.content)
            self.stats["analyzed_contexts"] += len(contexts)

            return analyses

        except Exception as e:
            logger.error(f"分析上下文失败: {e}")
            # 返回默认分析结果
            return [
                MemoryAnalysis(
                    importance=MemoryImportance.MEDIUM,
                    should_save_to_rag=False,
                    summary=str(ctx.content)[:100],
                    key_concepts=[],
                    reasoning="分析失败，使用默认值",
                    relevance_score=0.5,
                )
                for ctx in contexts
            ]

    def _build_analysis_prompt(self, context_summaries: List[Dict]) -> str:
        """构建分析prompt"""
        return f"""
请分析以下上下文信息的记忆价值。对每个上下文，请提供：

1. 重要性等级（1-5，5最重要）
2. 是否应存入RAG知识库（true/false）
3. 简要摘要（1-2句话）
4. 关键概念列表
5. 判断理由
6. 相关性评分（0-1）

需要分析的上下文：
{json.dumps(context_summaries, ensure_ascii=False, indent=2)}

请严格按照以下JSON格式回复：
```json
{{
  "analyses": [
    {{
      "index": 0,
      "importance": 4,
      "should_save_to_rag": true,
      "summary": "简要摘要",
      "key_concepts": ["概念1", "概念2"],
      "reasoning": "判断理由",
      "relevance_score": 0.8
    }}
  ]
}}
```

判断标准：
- 重要性5：关键决策、重要发现、核心算法
- 重要性4：有价值的信息、技术细节
- 重要性3：一般性信息、常规操作
- 重要性2：辅助信息、临时数据
- 重要性1：琐碎信息、日志记录

RAG存储标准：
- 具有长期价值的知识
- 可能被频繁查询的信息
- 技术文档、代码示例
- 重要的决策过程
"""

    def _parse_analysis_response(self, response: str) -> List[MemoryAnalysis]:
        """解析LLM的分析响应"""
        try:
            # 提取JSON部分
            start_idx = response.find("```json")
            end_idx = response.find("```", start_idx + 7)
            if start_idx != -1 and end_idx != -1:
                json_str = response[start_idx + 7 : end_idx].strip()
            else:
                json_str = response.strip()

            data = json.loads(json_str)
            analyses = []

            for item in data.get("analyses", []):
                analysis = MemoryAnalysis(
                    importance=MemoryImportance(item.get("importance", 3)),
                    should_save_to_rag=item.get("should_save_to_rag", False),
                    summary=item.get("summary", ""),
                    key_concepts=item.get("key_concepts", []),
                    reasoning=item.get("reasoning", ""),
                    relevance_score=item.get("relevance_score", 0.5),
                )
                analyses.append(analysis)

            return analyses

        except Exception as e:
            logger.error(f"解析分析响应失败: {e}")
            return []

    async def compress_context(self, context: BaseContext) -> BaseContext:
        """
        压缩上下文内容

        Args:
            context: 要压缩的上下文

        Returns:
            压缩后的上下文
        """
        if len(str(context.content)) <= self.max_context_length:
            return context

        prompt = f"""
请将以下内容压缩为简洁但信息完整的摘要，保留所有关键信息：

类型：{context.context_type.value}
标签：{', '.join(context.tags)}

内容：
{context.content}

请提供一个简洁的摘要，保留所有重要信息和技术细节。
"""

        try:
            response = await self.llm_client.ainvoke(prompt)

            compressed_content = response.content.strip()

            # 创建压缩后的上下文
            compressed_context = BaseContext(
                content=compressed_content,
                context_type=context.context_type,
                metadata={
                    **context.metadata,
                    "original_length": len(str(context.content)),
                    "compressed_at": datetime.now().isoformat(),
                    "compression_ratio": (
                        len(compressed_content) / len(str(context.content))
                    ),
                },
                priority=context.priority,
                tags=context.tags + ["compressed"],
                parent_id=context.id,
            )

            compressed_context.is_compressed = True
            self.stats["compressed_contexts"] += 1

            return compressed_context

        except Exception as e:
            logger.error(f"压缩上下文失败: {e}")
            return context

    async def process_context_for_long_term_storage(
        self, context: BaseContext
    ) -> Tuple[bool, Optional[BaseContext], MemoryAnalysis]:
        """
        处理上下文用于长期存储

        Args:
            context: 要处理的上下文

        Returns:
            (是否应保存, 处理后的上下文, 分析结果)
        """
        # 分析上下文
        analyses = await self.analyze_context_batch([context])
        if not analyses:
            return False, None, None

        analysis = analyses[0]

        # 判断是否应该保存
        if analysis.importance.value < self.importance_threshold.value:
            self.stats["rejected_contexts"] += 1
            return False, None, analysis

        # 压缩上下文（如果需要）
        processed_context = context
        if len(str(context.content)) > self.max_context_length:
            processed_context = await self.compress_context(context)

        # 更新元数据
        processed_context.metadata.update(
            {
                "memory_analysis": {
                    "importance": analysis.importance.value,
                    "summary": analysis.summary,
                    "key_concepts": analysis.key_concepts,
                    "reasoning": analysis.reasoning,
                    "relevance_score": analysis.relevance_score,
                    "should_save_to_rag": analysis.should_save_to_rag,
                    "analyzed_at": datetime.now().isoformat(),
                }
            }
        )

        return True, processed_context, analysis

    async def save_to_long_term_memory(
        self, context: BaseContext
    ) -> Tuple[bool, Optional[MemoryAnalysis]]:
        """
        保存上下文到长期记忆

        Args:
            context: 要保存的上下文

        Returns:
            (是否成功保存, 分析结果)
        """
        should_save, processed_context, analysis = (
            await self.process_context_for_long_term_storage(context)
        )

        if not should_save or not processed_context:
            return False, analysis

        # 保存到长期记忆
        success = await self.long_term_memory.save(processed_context)
        if success:
            self.stats["saved_to_long_term"] += 1

            # 如果需要保存到RAG
            if analysis and analysis.should_save_to_rag:
                await self._save_to_rag_knowledge_base(processed_context)
                self.stats["saved_to_rag"] += 1

        return success, analysis

    async def _save_to_rag_knowledge_base(self, context: BaseContext):
        """保存到RAG知识库"""
        try:
            # 这里可以集成具体的RAG系统
            # 暂时记录到日志
            logger.info(f"保存到RAG知识库: {context.id}")

            # 可以在这里调用具体的RAG系统API
            # 例如：await rag_system.add_document(context)

        except Exception as e:
            logger.error(f"保存到RAG知识库失败: {e}")

    async def batch_process_working_memory(
        self, context_manager: ContextManager, limit: int = 50
    ) -> Dict[str, Any]:
        """
        批量处理工作记忆中的上下文

        Args:
            context_manager: 上下文管理器
            limit: 处理数量限制

        Returns:
            处理统计信息
        """
        # 获取工作记忆中的上下文
        all_contexts = await context_manager.working_memory.get_all()

        # 按优先级和访问时间排序
        all_contexts.sort(key=lambda x: (x.priority.value, x.last_access), reverse=True)

        # 限制处理数量
        contexts_to_process = all_contexts[:limit]

        # 批量分析
        analyses = await self.analyze_context_batch(contexts_to_process)

        processed_stats = {
            "total_processed": len(contexts_to_process),
            "saved_to_long_term": 0,
            "saved_to_rag": 0,
            "compressed": 0,
            "rejected": 0,
        }

        # 逐个处理
        for context, analysis in zip(contexts_to_process, analyses):
            if analysis.importance.value >= self.importance_threshold.value:
                success, _ = await self.save_to_long_term_memory(context)
                if success:
                    processed_stats["saved_to_long_term"] += 1
                    if analysis.should_save_to_rag:
                        processed_stats["saved_to_rag"] += 1
                    if context.is_compressed:
                        processed_stats["compressed"] += 1
            else:
                processed_stats["rejected"] += 1

        return processed_stats

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "memory_stats": self.stats.copy(),
            "thresholds": {
                "importance_threshold": self.importance_threshold.value,
                "rag_threshold": self.rag_threshold,
                "max_context_length": self.max_context_length,
            },
        }


# 全局智能记忆管理器实例
_global_intelligent_memory_manager = None


def get_intelligent_memory_manager() -> IntelligentMemoryManager:
    """获取全局智能记忆管理器实例"""
    global _global_intelligent_memory_manager
    if _global_intelligent_memory_manager is None:
        _global_intelligent_memory_manager = IntelligentMemoryManager()
    return _global_intelligent_memory_manager
