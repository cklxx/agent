"""
RAG Context Manager - 将RAG检索结果管理为上下文
"""

import json
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from .base import ContextType, Priority
from .manager import ContextManager
from ..rag.enhanced_retriever import EnhancedRAGRetriever
from ..rag.code_retriever import CodeRetriever

logger = logging.getLogger(__name__)


class RAGContextManager:
    """RAG上下文管理器 - 将RAG检索结果转换为上下文"""

    def __init__(
        self,
        context_manager: ContextManager,
        repo_path: str,
        use_enhanced_retriever: bool = True,
    ):
        """
        初始化RAG上下文管理器

        Args:
            context_manager: Context管理器实例
            repo_path: 代码仓库路径
            use_enhanced_retriever: 是否使用增强检索器
        """
        self.context_manager = context_manager
        self.repo_path = Path(repo_path)
        self.use_enhanced_retriever = use_enhanced_retriever

        # 初始化检索器
        if use_enhanced_retriever:
            self.retriever = EnhancedRAGRetriever(
                repo_path=repo_path,
                db_path="temp/rag_data/enhanced_rag",
                use_intelligent_filter=True,
            )
        else:
            self.retriever = CodeRetriever(
                repo_path=repo_path, db_path="temp/rag_data/code_index.db"
            )

        logger.info(
            f"RAG上下文管理器初始化完成，仓库路径: {repo_path}, 增强检索: {use_enhanced_retriever}"
        )

    async def add_rag_search_context(
        self,
        query: str,
        max_results: int = 5,
        context_type: ContextType = ContextType.RAG_CODE,
        include_semantic: bool = False,
    ) -> List[str]:
        """
        执行RAG搜索并将结果添加为上下文

        Args:
            query: 搜索查询
            max_results: 最大结果数量
            context_type: 上下文类型
            include_semantic: 是否包含语义搜索结果

        Returns:
            添加的context ID列表
        """
        try:
            context_ids = []

            # 如果使用增强检索器
            if self.use_enhanced_retriever and hasattr(self.retriever, "hybrid_search"):
                retrieval_results = await self.retriever.hybrid_search(
                    query, n_results=max_results
                )

                for result in retrieval_results:
                    content = self._format_enhanced_result(result, query)
                    metadata = self._build_enhanced_metadata(result, query)
                    tags = self._build_enhanced_tags(result, query)

                    context_id = await self.context_manager.add_context(
                        content=content,
                        context_type=context_type,
                        metadata=metadata,
                        priority=Priority.HIGH,
                        tags=tags,
                    )
                    context_ids.append(context_id)

            else:
                # 使用基础检索器
                documents = self.retriever.query_relevant_documents(query)

                for i, doc in enumerate(documents[:max_results]):
                    content = self._format_document_result(doc, query)
                    metadata = self._build_document_metadata(doc, query)
                    tags = self._build_document_tags(doc, query)

                    context_id = await self.context_manager.add_context(
                        content=content,
                        context_type=context_type,
                        metadata=metadata,
                        priority=Priority.HIGH if i < 2 else Priority.MEDIUM,
                        tags=tags,
                    )
                    context_ids.append(context_id)

            logger.info(f"RAG搜索 '{query}' 添加了 {len(context_ids)} 个上下文")
            return context_ids

        except Exception as e:
            logger.error(f"RAG搜索添加上下文失败: {e}")
            return []

    async def add_function_search_context(self, function_name: str) -> List[str]:
        """搜索函数并添加上下文"""
        try:
            if hasattr(self.retriever, "search_by_function_name"):
                documents = self.retriever.search_by_function_name(function_name)
            else:
                # 回退到普通搜索
                documents = self.retriever.query_relevant_documents(
                    f"function {function_name}"
                )

            context_ids = []
            for doc in documents:
                content = self._format_function_result(doc, function_name)
                metadata = {
                    "source": "rag_function_search",
                    "function_name": function_name,
                    "file_path": getattr(doc, "id", "unknown"),
                    "search_type": "function",
                }

                tags = ["rag", "function", function_name]

                context_id = await self.context_manager.add_context(
                    content=content,
                    context_type=ContextType.RAG_CODE,
                    metadata=metadata,
                    priority=Priority.HIGH,
                    tags=tags,
                )
                context_ids.append(context_id)

            logger.info(
                f"函数搜索 '{function_name}' 添加了 {len(context_ids)} 个上下文"
            )
            return context_ids

        except Exception as e:
            logger.error(f"函数搜索添加上下文失败: {e}")
            return []

    async def add_class_search_context(self, class_name: str) -> List[str]:
        """搜索类并添加上下文"""
        try:
            if hasattr(self.retriever, "search_by_class_name"):
                documents = self.retriever.search_by_class_name(class_name)
            else:
                # 回退到普通搜索
                documents = self.retriever.query_relevant_documents(
                    f"class {class_name}"
                )

            context_ids = []
            for doc in documents:
                content = self._format_class_result(doc, class_name)
                metadata = {
                    "source": "rag_class_search",
                    "class_name": class_name,
                    "file_path": getattr(doc, "id", "unknown"),
                    "search_type": "class",
                }

                tags = ["rag", "class", class_name]

                context_id = await self.context_manager.add_context(
                    content=content,
                    context_type=ContextType.RAG_CODE,
                    metadata=metadata,
                    priority=Priority.HIGH,
                    tags=tags,
                )
                context_ids.append(context_id)

            logger.info(f"类搜索 '{class_name}' 添加了 {len(context_ids)} 个上下文")
            return context_ids

        except Exception as e:
            logger.error(f"类搜索添加上下文失败: {e}")
            return []

    def _format_enhanced_result(self, result, query: str) -> str:
        """格式化增强检索结果"""
        doc = result.document
        content_parts = [
            f"# RAG检索结果: {doc.title}",
            f"查询: {query}",
            f"综合得分: {result.combined_score:.3f} (向量: {result.vector_score:.3f}, 关键词: {result.keyword_score:.3f})",
            f"检索方法: {result.retrieval_method}",
            "",
        ]

        for i, chunk in enumerate(doc.chunks):
            content_parts.append(f"## 代码块 {i+1} (相关性: {chunk.similarity:.3f})")
            content_parts.append("```")
            content_parts.append(chunk.content)
            content_parts.append("```")
            content_parts.append("")

        return "\n".join(content_parts)

    def _format_document_result(self, doc, query: str) -> str:
        """格式化文档检索结果"""
        content_parts = [
            f"# RAG检索结果: {doc.title}",
            f"查询: {query}",
            f"文件: {getattr(doc, 'id', 'unknown')}",
            "",
        ]

        for i, chunk in enumerate(doc.chunks):
            content_parts.append(f"## 代码块 {i+1} (相关性: {chunk.similarity:.3f})")
            content_parts.append("```")
            content_parts.append(chunk.content)
            content_parts.append("```")
            content_parts.append("")

        return "\n".join(content_parts)

    def _format_function_result(self, doc, function_name: str) -> str:
        """格式化函数检索结果"""
        content_parts = [
            f"# 函数定义: {function_name}",
            f"位置: {getattr(doc, 'url', getattr(doc, 'id', 'unknown'))}",
            "",
        ]

        if doc.chunks:
            content_parts.append("## 函数代码")
            content_parts.append("```python")
            content_parts.append(doc.chunks[0].content)
            content_parts.append("```")

        return "\n".join(content_parts)

    def _format_class_result(self, doc, class_name: str) -> str:
        """格式化类检索结果"""
        content_parts = [
            f"# 类定义: {class_name}",
            f"位置: {getattr(doc, 'url', getattr(doc, 'id', 'unknown'))}",
            "",
        ]

        if doc.chunks:
            content_parts.append("## 类代码")
            content_parts.append("```python")
            content_parts.append(doc.chunks[0].content)
            content_parts.append("```")

        return "\n".join(content_parts)

    def _build_enhanced_metadata(self, result, query: str) -> Dict[str, Any]:
        """构建增强检索结果的元数据"""
        doc = result.document
        return {
            "source": "enhanced_rag",
            "query": query,
            "file_path": getattr(doc, "id", "unknown"),
            "url": getattr(doc, "url", ""),
            "combined_score": result.combined_score,
            "vector_score": result.vector_score,
            "keyword_score": result.keyword_score,
            "retrieval_method": result.retrieval_method,
            "chunk_count": len(doc.chunks),
        }

    def _build_document_metadata(self, doc, query: str) -> Dict[str, Any]:
        """构建文档检索结果的元数据"""
        return {
            "source": "code_rag",
            "query": query,
            "file_path": getattr(doc, "id", "unknown"),
            "url": getattr(doc, "url", ""),
            "chunk_count": len(doc.chunks),
        }

    def _build_enhanced_tags(self, result, query: str) -> List[str]:
        """构建增强检索结果的标签"""
        tags = ["rag", "enhanced", result.retrieval_method]

        # 从文件路径提取语言标签
        doc = result.document
        file_path = getattr(doc, "id", "")
        if file_path:
            suffix = Path(file_path).suffix[1:] if Path(file_path).suffix else "unknown"
            tags.append(suffix)

        return tags

    def _build_document_tags(self, doc, query: str) -> List[str]:
        """构建文档检索结果的标签"""
        tags = ["rag", "code"]

        # 从文件路径提取语言标签
        file_path = getattr(doc, "id", "")
        if file_path:
            suffix = Path(file_path).suffix[1:] if Path(file_path).suffix else "unknown"
            tags.append(suffix)

        return tags

    async def get_rag_context_summary(self) -> Dict[str, Any]:
        """获取RAG上下文摘要"""
        try:
            # 搜索所有RAG相关的上下文
            rag_contexts = await self.context_manager.search_contexts(
                query="", context_type=ContextType.RAG_CODE, limit=100
            )

            # 统计信息
            summary = {
                "total_rag_contexts": len(rag_contexts),
                "sources": {},
                "search_types": {},
                "file_types": {},
            }

            for context in rag_contexts:
                metadata = context.metadata

                # 统计来源
                source = metadata.get("source", "unknown")
                summary["sources"][source] = summary["sources"].get(source, 0) + 1

                # 统计搜索类型
                search_type = metadata.get("search_type", "general")
                summary["search_types"][search_type] = (
                    summary["search_types"].get(search_type, 0) + 1
                )

                # 统计文件类型
                file_path = metadata.get("file_path", "")
                if file_path:
                    suffix = (
                        Path(file_path).suffix[1:]
                        if Path(file_path).suffix
                        else "unknown"
                    )
                    summary["file_types"][suffix] = (
                        summary["file_types"].get(suffix, 0) + 1
                    )

            return summary

        except Exception as e:
            logger.error(f"获取RAG上下文摘要失败: {e}")
            return {"error": str(e)}

    async def get_rag_context_summary_text(self) -> str:
        summary = await self.get_rag_context_summary()
        # 将summary转换为markdown格式, 英文格式
        markdown_summary = ""
        markdown_summary += f"## Context Summary\n"
        markdown_summary += f"### Sources: {summary['sources']}\n"
        markdown_summary += f"### Search Types: {summary['search_types']}\n"
        markdown_summary += f"### File Types: {summary['file_types']}\n"
        return markdown_summary
