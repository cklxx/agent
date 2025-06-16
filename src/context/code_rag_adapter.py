"""
代码RAG适配器 - 将代码检索能力集成到Context管理模块
"""

import logging
from typing import List, Dict, Any
from pathlib import Path

from .base import ContextType, Priority
from .manager import ContextManager
from src.rag.code_retriever import CodeRetriever

logger = logging.getLogger(__name__)


class CodeRAGAdapter:
    """代码RAG适配器"""

    def __init__(
        self,
        context_manager: ContextManager,
        repo_path: str,
        db_path: str = "temp/rag_data/code_index.db",
    ):
        """
        初始化代码RAG适配器

        Args:
            context_manager: Context管理器实例
            repo_path: 代码仓库路径
            db_path: 索引数据库路径
        """
        self.context_manager = context_manager
        self.code_retriever = CodeRetriever(repo_path, db_path)
        self.repo_path = Path(repo_path)

        logger.info(f"代码RAG适配器初始化完成，仓库路径: {repo_path}")

    async def enhance_context_with_code(
        self,
        query: str,
        context_type: ContextType = ContextType.CODE,
        max_results: int = 5,
    ) -> List[str]:
        """
        使用代码检索增强context

        Args:
            query: 查询关键词
            context_type: context类型
            max_results: 最大结果数量

        Returns:
            添加的context ID列表
        """
        try:
            # 使用代码检索器搜索相关代码
            documents = self.code_retriever.query_relevant_documents(query)

            context_ids = []
            for i, doc in enumerate(documents[:max_results]):
                # 构建代码context内容
                content = self._format_code_document(doc)

                # 构建元数据
                metadata = {
                    "source": "code_rag",
                    "file_path": doc.id,
                    "url": doc.url,
                    "language": self._extract_language_from_title(doc.title),
                    "chunk_count": len(doc.chunks),
                    "query": query,
                }

                # 生成标签
                tags = [
                    "code",
                    "rag",
                    metadata["language"],
                    Path(doc.id).suffix[1:] if Path(doc.id).suffix else "unknown",
                ]

                # 添加到context管理器
                context_id = await self.context_manager.add_context(
                    content=content,
                    context_type=context_type,
                    metadata=metadata,
                    priority=Priority.HIGH if i < 2 else Priority.MEDIUM,
                    tags=tags,
                )

                context_ids.append(context_id)

            logger.info(f"为查询 '{query}' 添加了 {len(context_ids)} 个代码context")
            return context_ids

        except Exception as e:
            logger.error(f"代码RAG增强失败: {e}")
            return []

    async def search_and_add_function_context(self, function_name: str) -> List[str]:
        """搜索并添加函数相关的context"""
        try:
            documents = self.code_retriever.search_by_function_name(function_name)

            context_ids = []
            for doc in documents:
                content = self._format_function_document(doc)

                metadata = {
                    "source": "code_rag",
                    "function_name": function_name,
                    "file_path": doc.id.split(":")[0],
                    "url": doc.url,
                    "type": "function_definition",
                }

                tags = ["code", "function", function_name]

                context_id = await self.context_manager.add_context(
                    content=content,
                    context_type=ContextType.CODE,
                    metadata=metadata,
                    priority=Priority.HIGH,
                    tags=tags,
                )

                context_ids.append(context_id)

            logger.info(f"为函数 '{function_name}' 添加了 {len(context_ids)} 个context")
            return context_ids

        except Exception as e:
            logger.error(f"搜索函数context失败: {e}")
            return []

    async def search_and_add_class_context(self, class_name: str) -> List[str]:
        """搜索并添加类相关的context"""
        try:
            documents = self.code_retriever.search_by_class_name(class_name)

            context_ids = []
            for doc in documents:
                content = self._format_class_document(doc)

                metadata = {
                    "source": "code_rag",
                    "class_name": class_name,
                    "file_path": doc.id.split(":")[0],
                    "url": doc.url,
                    "type": "class_definition",
                }

                tags = ["code", "class", class_name]

                context_id = await self.context_manager.add_context(
                    content=content,
                    context_type=ContextType.CODE,
                    metadata=metadata,
                    priority=Priority.HIGH,
                    tags=tags,
                )

                context_ids.append(context_id)

            logger.info(f"为类 '{class_name}' 添加了 {len(context_ids)} 个context")
            return context_ids

        except Exception as e:
            logger.error(f"搜索类context失败: {e}")
            return []

    def _format_code_document(self, doc) -> str:
        """格式化代码文档为context内容"""
        content_parts = [
            f"# 代码文件: {doc.title}",
            f"文件路径: {doc.id}",
            f"代码块数量: {len(doc.chunks)}",
            "",
        ]

        for i, chunk in enumerate(doc.chunks):
            content_parts.append(f"## 代码块 {i+1} (相关性: {chunk.similarity:.2f})")
            content_parts.append("```")
            content_parts.append(chunk.content)
            content_parts.append("```")
            content_parts.append("")

        return "\n".join(content_parts)

    def _format_function_document(self, doc) -> str:
        """格式化函数文档"""
        content_parts = [f"# 函数定义: {doc.title}", f"位置: {doc.url}", ""]

        if doc.chunks:
            content_parts.append("## 函数代码")
            content_parts.append("```python")
            content_parts.append(doc.chunks[0].content)
            content_parts.append("```")

        return "\n".join(content_parts)

    def _format_class_document(self, doc) -> str:
        """格式化类文档"""
        content_parts = [f"# 类定义: {doc.title}", f"位置: {doc.url}", ""]

        if doc.chunks:
            content_parts.append("## 类代码")
            content_parts.append("```python")
            content_parts.append(doc.chunks[0].content)
            content_parts.append("```")

        return "\n".join(content_parts)

    def _extract_language_from_title(self, title: str) -> str:
        """从标题中提取语言类型"""
        if "(" in title and ")" in title:
            lang_part = title.split("(")[-1].split(")")[0]
            return lang_part.lower()
        return "unknown"

    async def get_code_context_summary(self) -> Dict[str, Any]:
        """获取代码context的摘要信息"""
        try:
            # 获取所有代码相关的context
            code_contexts = await self.context_manager.search_contexts(
                query="", context_type=ContextType.CODE, tags=["code"], limit=100
            )

            # 统计信息
            summary = {
                "total_code_contexts": len(code_contexts),
                "sources": {},
                "languages": {},
                "types": {},
                "recent_queries": [],
            }

            for context in code_contexts:
                metadata = context.metadata

                # 统计来源
                source = metadata.get("source", "unknown")
                summary["sources"][source] = summary["sources"].get(source, 0) + 1

                # 统计语言
                language = metadata.get("language", "unknown")
                summary["languages"][language] = (
                    summary["languages"].get(language, 0) + 1
                )

                # 统计类型
                context_type = metadata.get("type", "unknown")
                summary["types"][context_type] = (
                    summary["types"].get(context_type, 0) + 1
                )

                # 收集查询记录
                query = metadata.get("query")
                if query and query not in summary["recent_queries"]:
                    summary["recent_queries"].append(query)

            # 限制查询记录数量
            summary["recent_queries"] = summary["recent_queries"][-10:]

            # 获取索引器统计
            indexer_stats = self.code_retriever.get_indexer_statistics()
            summary["indexer_stats"] = indexer_stats

            return summary

        except Exception as e:
            logger.error(f"获取代码context摘要失败: {e}")
            return {}

    async def auto_enhance_code_context(self, query: str) -> Dict[str, Any]:
        """自动增强代码相关的context"""
        result = {"query": query, "enhanced_contexts": [], "suggestions": []}

        try:
            # 1. 通用代码搜索
            general_contexts = await self.enhance_context_with_code(query)
            result["enhanced_contexts"].extend(general_contexts)

            logger.info(
                f"自动增强完成，添加了 {len(result['enhanced_contexts'])} 个context"
            )

        except Exception as e:
            logger.error(f"自动增强代码context失败: {e}")

        return result
