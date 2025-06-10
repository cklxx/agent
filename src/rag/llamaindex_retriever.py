"""
LlamaIndex集成的检索器
实现向量召回和倒排索引召回相结合的混合检索功能
"""

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional, Tuple, Union
from pathlib import Path
import json

try:
    from llama_index.core import Document, VectorStoreIndex, StorageContext
    from llama_index.core.node_parser import SimpleNodeParser
    from llama_index.core.embeddings import BaseEmbedding
    from llama_index.core.vector_stores import VectorStore
    from llama_index.core.retrievers import VectorIndexRetriever, BaseRetriever
    from llama_index.core.query_engine import RetrieverQueryEngine
    from llama_index.core.response.schema import Response
    from llama_index.core.schema import NodeWithScore, MetadataMode
    from llama_index.core.vector_stores import SimpleVectorStore
    from llama_index.core.storage.docstore import SimpleDocumentStore
    from llama_index.core.storage.index_store import SimpleIndexStore
    from llama_index.core.postprocessor import SimilarityPostprocessor
    from llama_index.core import Settings

    # 尝试导入BM25检索器（倒排索引）
    try:
        from llama_index.core.retrievers import BM25Retriever

        HAS_BM25 = True
    except ImportError:
        HAS_BM25 = False

    LLAMA_INDEX_AVAILABLE = True
except ImportError:
    LLAMA_INDEX_AVAILABLE = False
    HAS_BM25 = False

from ..context.base import BaseContext, ContextType
from ..llms.llm_factory import create_llm_client

logger = logging.getLogger(__name__)


class HybridLlamaIndexRetriever:
    """
    混合LlamaIndex检索器
    结合向量召回和倒排索引召回（BM25）
    """

    def __init__(
        self,
        storage_dir: str = "temp/rag_data/llamaindex",
        embedding_model: Optional[BaseEmbedding] = None,
        similarity_threshold: float = 0.7,
        top_k_vector: int = 10,
        top_k_bm25: int = 10,
        alpha: float = 0.5,  # 向量检索和BM25检索的权重平衡
    ):
        """
        初始化混合检索器

        Args:
            storage_dir: 存储目录
            embedding_model: 嵌入模型
            similarity_threshold: 相似度阈值
            top_k_vector: 向量检索返回的top-k数量
            top_k_bm25: BM25检索返回的top-k数量
            alpha: 向量检索权重 (1-alpha为BM25权重)
        """
        if not LLAMA_INDEX_AVAILABLE:
            raise ImportError("LlamaIndex 未安装。请运行: pip install llama-index")

        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.similarity_threshold = similarity_threshold
        self.top_k_vector = top_k_vector
        self.top_k_bm25 = top_k_bm25
        self.alpha = alpha

        # 设置嵌入模型
        if embedding_model:
            Settings.embed_model = embedding_model

        # 初始化存储组件
        self.storage_context = None
        self.vector_index = None
        self.vector_retriever = None
        self.bm25_retriever = None
        self.nodes = []  # 存储所有节点用于BM25

        # 加载或初始化索引
        self._initialize_storage()

        logger.info(f"HybridLlamaIndexRetriever初始化完成，存储目录: {storage_dir}")

    def _initialize_storage(self):
        """初始化存储和索引"""
        try:
            # 检查是否存在已有的索引
            if (self.storage_dir / "vector_store.json").exists():
                logger.info("加载现有的LlamaIndex索引")
                self._load_existing_index()
            else:
                logger.info("创建新的LlamaIndex索引")
                self._create_new_index()

        except Exception as e:
            logger.error(f"初始化存储失败: {e}")
            self._create_new_index()

    def _create_new_index(self):
        """创建新的索引"""
        # 创建存储上下文
        vector_store = SimpleVectorStore()
        docstore = SimpleDocumentStore()
        index_store = SimpleIndexStore()

        self.storage_context = StorageContext.from_defaults(
            vector_store=vector_store,
            docstore=docstore,
            index_store=index_store,
        )

        # 创建空的向量索引
        self.vector_index = VectorStoreIndex.from_documents(
            [], storage_context=self.storage_context
        )

        # 创建检索器
        self.vector_retriever = VectorIndexRetriever(
            index=self.vector_index,
            similarity_top_k=self.top_k_vector,
        )

    def _load_existing_index(self):
        """加载现有的索引"""
        # 从存储目录恢复
        self.storage_context = StorageContext.from_defaults(
            persist_dir=str(self.storage_dir)
        )

        # 加载向量索引
        self.vector_index = VectorStoreIndex.from_documents(
            [], storage_context=self.storage_context
        )

        # 创建检索器
        self.vector_retriever = VectorIndexRetriever(
            index=self.vector_index,
            similarity_top_k=self.top_k_vector,
        )

        # 加载节点用于BM25
        self._load_nodes_for_bm25()

    def _load_nodes_for_bm25(self):
        """加载节点用于BM25检索"""
        try:
            nodes_file = self.storage_dir / "nodes.json"
            if nodes_file.exists():
                with open(nodes_file, "r", encoding="utf-8") as f:
                    nodes_data = json.load(f)

                # 重建节点对象
                from llama_index.core.schema import TextNode

                self.nodes = []
                for node_data in nodes_data:
                    node = TextNode(
                        text=node_data["text"],
                        metadata=node_data.get("metadata", {}),
                        id_=node_data.get("id_"),
                    )
                    self.nodes.append(node)

                # 创建BM25检索器
                self._create_bm25_retriever()

        except Exception as e:
            logger.error(f"加载BM25节点失败: {e}")

    def _create_bm25_retriever(self):
        """创建BM25检索器"""
        if HAS_BM25 and self.nodes:
            try:
                self.bm25_retriever = BM25Retriever.from_defaults(
                    nodes=self.nodes,
                    similarity_top_k=self.top_k_bm25,
                )
                logger.info(f"BM25检索器创建成功，共 {len(self.nodes)} 个节点")
            except Exception as e:
                logger.error(f"创建BM25检索器失败: {e}")
                self.bm25_retriever = None
        else:
            logger.warning("BM25检索器不可用")
            self.bm25_retriever = None

    def _save_nodes_for_bm25(self):
        """保存节点数据用于BM25"""
        try:
            nodes_file = self.storage_dir / "nodes.json"
            nodes_data = []
            for node in self.nodes:
                nodes_data.append(
                    {"id_": node.node_id, "text": node.text, "metadata": node.metadata}
                )

            with open(nodes_file, "w", encoding="utf-8") as f:
                json.dump(nodes_data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"保存BM25节点失败: {e}")

    async def add_contexts(self, contexts: List[BaseContext]) -> bool:
        """
        添加上下文到索引

        Args:
            contexts: 要添加的上下文列表

        Returns:
            是否成功
        """
        if not contexts:
            return True

        try:
            # 转换上下文为LlamaIndex文档
            documents = []
            for ctx in contexts:
                # 构建文档内容
                content = self._context_to_content(ctx)

                # 创建文档
                doc = Document(
                    text=content,
                    metadata={
                        "context_id": ctx.id,
                        "context_type": ctx.context_type.value,
                        "priority": ctx.priority.value,
                        "tags": ctx.tags,
                        "timestamp": ctx.timestamp.isoformat(),
                        "source": "context_manager",
                    },
                )
                documents.append(doc)

            # 解析文档为节点
            parser = SimpleNodeParser()
            nodes = parser.get_nodes_from_documents(documents)

            # 添加到向量索引
            self.vector_index.insert_nodes(nodes)

            # 添加到BM25节点列表
            self.nodes.extend(nodes)

            # 重新创建BM25检索器
            self._create_bm25_retriever()

            # 持久化存储
            self._persist_storage()

            logger.info(f"成功添加 {len(contexts)} 个上下文到索引")
            return True

        except Exception as e:
            logger.error(f"添加上下文到索引失败: {e}")
            return False

    def _context_to_content(self, context: BaseContext) -> str:
        """将上下文转换为可搜索的内容"""
        content_parts = []

        # 添加类型信息
        content_parts.append(f"类型: {context.context_type.value}")

        # 添加标签
        if context.tags:
            content_parts.append(f"标签: {', '.join(context.tags)}")

        # 添加主要内容
        if isinstance(context.content, dict):
            # 如果是字典，提取关键信息
            for key, value in context.content.items():
                content_parts.append(f"{key}: {value}")
        else:
            content_parts.append(str(context.content))

        # 添加元数据
        if context.metadata:
            for key, value in context.metadata.items():
                if key not in ["context_id", "timestamp"]:  # 避免重复
                    content_parts.append(f"{key}: {value}")

        return "\n".join(content_parts)

    async def search(
        self,
        query: str,
        context_types: Optional[List[ContextType]] = None,
        tags: Optional[List[str]] = None,
        limit: int = 10,
    ) -> List[Tuple[BaseContext, float]]:
        """
        混合搜索上下文

        Args:
            query: 搜索查询
            context_types: 上下文类型过滤
            tags: 标签过滤
            limit: 结果限制

        Returns:
            (上下文, 相似度分数)的元组列表
        """
        try:
            # 向量检索结果
            vector_results = []
            if self.vector_retriever:
                vector_nodes = await self._vector_search(query)
                vector_results = self._nodes_to_contexts(vector_nodes, "vector")

            # BM25检索结果
            bm25_results = []
            if self.bm25_retriever:
                bm25_nodes = await self._bm25_search(query)
                bm25_results = self._nodes_to_contexts(bm25_nodes, "bm25")

            # 合并和排序结果
            combined_results = self._combine_results(vector_results, bm25_results)

            # 应用过滤器
            filtered_results = self._apply_filters(
                combined_results, context_types, tags
            )

            # 去重并限制结果数量
            final_results = self._deduplicate_and_limit(filtered_results, limit)

            logger.info(
                f"混合搜索完成: 向量结果={len(vector_results)}, "
                f"BM25结果={len(bm25_results)}, 最终结果={len(final_results)}"
            )

            return final_results

        except Exception as e:
            logger.error(f"混合搜索失败: {e}")
            return []

    async def _vector_search(self, query: str) -> List[NodeWithScore]:
        """向量搜索"""
        try:
            nodes = self.vector_retriever.retrieve(query)
            return nodes
        except Exception as e:
            logger.error(f"向量搜索失败: {e}")
            return []

    async def _bm25_search(self, query: str) -> List[NodeWithScore]:
        """BM25搜索"""
        try:
            if self.bm25_retriever:
                nodes = self.bm25_retriever.retrieve(query)
                return nodes
            return []
        except Exception as e:
            logger.error(f"BM25搜索失败: {e}")
            return []

    def _nodes_to_contexts(
        self, nodes: List[NodeWithScore], search_type: str
    ) -> List[Tuple[BaseContext, float, str]]:
        """将节点转换为上下文"""
        results = []
        for node_with_score in nodes:
            try:
                node = node_with_score.node
                score = node_with_score.score or 0.0

                # 从元数据重建上下文
                metadata = node.metadata

                # 构建BaseContext
                context = BaseContext(
                    id=metadata.get("context_id", node.node_id),
                    content=node.text,  # 使用节点文本作为内容
                    context_type=ContextType(metadata.get("context_type", "GENERAL")),
                    metadata=metadata,
                    tags=metadata.get("tags", []),
                )

                results.append((context, score, search_type))

            except Exception as e:
                logger.error(f"转换节点到上下文失败: {e}")
                continue

        return results

    def _combine_results(
        self,
        vector_results: List[Tuple[BaseContext, float, str]],
        bm25_results: List[Tuple[BaseContext, float, str]],
    ) -> List[Tuple[BaseContext, float, str]]:
        """合并向量和BM25搜索结果"""

        # 标准化分数到0-1范围
        def normalize_scores(
            results: List[Tuple[BaseContext, float, str]],
        ) -> List[Tuple[BaseContext, float, str]]:
            if not results:
                return results

            scores = [score for _, score, _ in results]
            min_score = min(scores) if scores else 0
            max_score = max(scores) if scores else 1
            score_range = max_score - min_score if max_score != min_score else 1

            normalized = []
            for context, score, search_type in results:
                normalized_score = (score - min_score) / score_range
                normalized.append((context, normalized_score, search_type))

            return normalized

        # 标准化分数
        normalized_vector = normalize_scores(vector_results)
        normalized_bm25 = normalize_scores(bm25_results)

        # 合并结果
        all_results = []

        # 添加向量结果（权重为alpha）
        for context, score, search_type in normalized_vector:
            weighted_score = self.alpha * score
            all_results.append((context, weighted_score, f"{search_type}_weighted"))

        # 添加BM25结果（权重为1-alpha）
        for context, score, search_type in normalized_bm25:
            weighted_score = (1 - self.alpha) * score
            all_results.append((context, weighted_score, f"{search_type}_weighted"))

        return all_results

    def _apply_filters(
        self,
        results: List[Tuple[BaseContext, float, str]],
        context_types: Optional[List[ContextType]] = None,
        tags: Optional[List[str]] = None,
    ) -> List[Tuple[BaseContext, float, str]]:
        """应用过滤器"""
        filtered = results

        # 按上下文类型过滤
        if context_types:
            type_set = set(context_types)
            filtered = [
                (ctx, score, search_type)
                for ctx, score, search_type in filtered
                if ctx.context_type in type_set
            ]

        # 按标签过滤
        if tags:
            tag_set = set(tags)
            filtered = [
                (ctx, score, search_type)
                for ctx, score, search_type in filtered
                if tag_set.intersection(set(ctx.tags))
            ]

        return filtered

    def _deduplicate_and_limit(
        self, results: List[Tuple[BaseContext, float, str]], limit: int
    ) -> List[Tuple[BaseContext, float]]:
        """去重并限制结果数量"""
        # 按上下文ID去重，保留最高分数
        unique_results = {}
        for context, score, search_type in results:
            if (
                context.id not in unique_results
                or score > unique_results[context.id][1]
            ):
                unique_results[context.id] = (context, score)

        # 转换为列表并按分数排序
        final_results = list(unique_results.values())
        final_results.sort(key=lambda x: x[1], reverse=True)

        # 应用相似度阈值过滤
        filtered_results = [
            (ctx, score)
            for ctx, score in final_results
            if score >= self.similarity_threshold
        ]

        return filtered_results[:limit]

    def _persist_storage(self):
        """持久化存储"""
        try:
            # 保存向量索引
            self.storage_context.persist(persist_dir=str(self.storage_dir))

            # 保存BM25节点
            self._save_nodes_for_bm25()

            logger.debug("索引持久化完成")

        except Exception as e:
            logger.error(f"持久化存储失败: {e}")

    async def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = {
            "total_nodes": len(self.nodes),
            "vector_index_available": self.vector_index is not None,
            "bm25_available": self.bm25_retriever is not None,
            "storage_dir": str(self.storage_dir),
            "settings": {
                "similarity_threshold": self.similarity_threshold,
                "top_k_vector": self.top_k_vector,
                "top_k_bm25": self.top_k_bm25,
                "alpha": self.alpha,
            },
        }

        # 添加向量索引统计
        if self.vector_index:
            try:
                # 这里可以添加更多向量索引的统计信息
                stats["vector_store_type"] = type(
                    self.vector_index._vector_store
                ).__name__
            except:
                pass

        return stats


# 全局LlamaIndex检索器实例
_global_llamaindex_retriever = None


def get_llamaindex_retriever() -> Optional[HybridLlamaIndexRetriever]:
    """获取全局LlamaIndex检索器实例"""
    global _global_llamaindex_retriever
    if _global_llamaindex_retriever is None and LLAMA_INDEX_AVAILABLE:
        try:
            _global_llamaindex_retriever = HybridLlamaIndexRetriever()
        except Exception as e:
            logger.error(f"创建LlamaIndex检索器失败: {e}")
            return None
    return _global_llamaindex_retriever


def is_llamaindex_available() -> bool:
    """检查LlamaIndex是否可用"""
    return LLAMA_INDEX_AVAILABLE
