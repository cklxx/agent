"""
增强的RAG检索器 - 结合embedding向量相似度和倒排索引召回
"""

import os
import json
import sqlite3
import logging
import numpy as np
import asyncio
import yaml
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import chromadb
from chromadb.config import Settings

from .retriever import Retriever, Resource, Document, Chunk
from .code_retriever import CodeRetriever

logger = logging.getLogger(__name__)


def load_embedding_config() -> Dict[str, Any]:
    """加载embedding配置"""
    try:
        # 首先检查环境变量中的DASHSCOPE_API_KEY
        dashscope_key = os.getenv("DASHSCOPE_API_KEY")
        if dashscope_key:
            return {
                "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                "model": "text-embedding-v4",
                "api_key": dashscope_key,
                "dimensions": 1024,
                "encoding_format": "float",
            }

        # 检查其他常见的API密钥
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key and openai_key != "sk-test":
            return {
                "base_url": "https://api.openai.com/v1",
                "model": "text-embedding-3-small",
                "api_key": openai_key,
                "dimensions": 1536,
                "encoding_format": "float",
            }

        # 如果都没有找到，使用配置文件
        config_path = Path(__file__).parent.parent / "config" / "embedding_config.yaml"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                dashscope_config = config.get("dashscope", {})

                # 替换环境变量占位符
                api_key = dashscope_config.get("api_key", "")
                if api_key.startswith("${") and api_key.endswith("}"):
                    env_var = api_key[2:-1]
                    api_key = os.getenv(env_var, "")

                if api_key:
                    dashscope_config["api_key"] = api_key
                    return dashscope_config

        # 最后的fallback
        logger.warning("未找到有效的embedding API配置，使用fallback配置")
        return {
            "base_url": "https://api.openai.com/v1",
            "model": "text-embedding-3-small",
            "api_key": "sk-fallback",
        }

    except Exception as e:
        logger.error(f"加载embedding配置失败: {e}")
        return {
            "base_url": "https://api.openai.com/v1",
            "model": "text-embedding-3-small",
            "api_key": "sk-fallback",
        }


@dataclass
class RetrievalResult:
    """检索结果"""

    document: Document
    vector_score: float = 0.0
    keyword_score: float = 0.0
    combined_score: float = 0.0
    retrieval_method: str = "hybrid"  # vector, keyword, hybrid


class EmbeddingClient:
    """Embedding客户端 - 使用OpenAI兼容的API"""

    def __init__(self, model_config: Dict[str, Any]):
        self.config = model_config
        self.api_key = model_config.get("api_key", "")
        self.base_url = model_config.get("base_url", "https://api.openai.com/v1")
        self.model = model_config.get("model", "text-embedding-3-small")
        self.dimensions = model_config.get("dimensions", 1536)
        self.encoding_format = model_config.get("encoding_format", "float")

        # Store model_config for backward compatibility
        self.model_config = model_config

    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """获取文本的embedding向量"""
        try:
            import httpx

            # 使用httpx调用embedding API
            async with httpx.AsyncClient() as client:
                # 构建请求参数
                request_data = {"model": self.model, "input": texts}

                # 添加可选参数
                if self.dimensions:
                    request_data["dimensions"] = self.dimensions
                if self.encoding_format:
                    request_data["encoding_format"] = self.encoding_format

                response = await client.post(
                    f"{self.base_url}/embeddings",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=request_data,
                    timeout=30.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    embeddings = [item["embedding"] for item in data["data"]]
                    return embeddings
                else:
                    logger.error(
                        f"Embedding API错误: {response.status_code} - {response.text}"
                    )
                    # 返回随机向量作为fallback
                    return [[0.0] * 1536 for _ in texts]

        except Exception as e:
            logger.error(f"获取embedding失败: {e}")
            # 返回随机向量作为fallback
            return [[0.0] * 1536 for _ in texts]


class VectorStore:
    """向量存储"""

    def __init__(self, db_path: str = "temp/rag_data/vector_store"):
        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)

        # 初始化ChromaDB
        self.client = chromadb.PersistentClient(
            path=str(self.db_path), settings=Settings(anonymized_telemetry=False)
        )

        # 获取或创建集合
        self.collection = self.client.get_or_create_collection(
            name="code_chunks", metadata={"description": "代码块向量存储"}
        )

    def add_documents(
        self, documents: List[Dict[str, Any]], embeddings: List[List[float]]
    ):
        """添加文档到向量存储"""
        try:
            ids = [doc["id"] for doc in documents]
            metadatas = [doc.get("metadata", {}) for doc in documents]
            texts = [doc["content"] for doc in documents]

            self.collection.add(
                embeddings=embeddings, documents=texts, metadatas=metadatas, ids=ids
            )
            logger.info(f"添加了 {len(documents)} 个文档到向量存储")

        except Exception as e:
            logger.error(f"添加文档到向量存储失败: {e}")

    def search(
        self, query_embedding: List[float], n_results: int = 10
    ) -> List[Dict[str, Any]]:
        """向量相似度搜索"""
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding], n_results=n_results
            )

            documents = []
            for i in range(len(results["ids"][0])):
                documents.append(
                    {
                        "id": results["ids"][0][i],
                        "content": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i],
                        "distance": (
                            results["distances"][0][i]
                            if "distances" in results
                            else 0.0
                        ),
                    }
                )

            return documents

        except Exception as e:
            logger.error(f"向量搜索失败: {e}")
            return []

    def count(self) -> int:
        """获取文档数量"""
        try:
            return self.collection.count()
        except:
            return 0


class KeywordIndex:
    """关键词倒排索引"""

    def __init__(self, db_path: str = "temp/rag_data/keyword_index.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=10000,
            stop_words=None,  # 保留停用词，因为代码中的常见词可能有意义
            ngram_range=(1, 2),  # 包含单词和双词组合
            lowercase=True,
        )
        self.tfidf_matrix = None
        self.documents = []
        self._init_db()

    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS keyword_index (
                id TEXT PRIMARY KEY,
                content TEXT,
                metadata TEXT,
                tfidf_vector TEXT
            )
        """
        )

        conn.commit()
        conn.close()

    def build_index(self, documents: List[Dict[str, Any]]):
        """构建倒排索引"""
        try:
            self.documents = documents
            texts = [doc["content"] for doc in documents]

            # 构建TF-IDF矩阵
            self.tfidf_matrix = self.tfidf_vectorizer.fit_transform(texts)

            # 保存到数据库
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 清空旧数据
            cursor.execute("DELETE FROM keyword_index")

            for i, doc in enumerate(documents):
                tfidf_vector = self.tfidf_matrix[i].toarray().tolist()
                cursor.execute(
                    """
                    INSERT INTO keyword_index (id, content, metadata, tfidf_vector)
                    VALUES (?, ?, ?, ?)
                """,
                    (
                        doc["id"],
                        doc["content"],
                        json.dumps(doc.get("metadata", {})),
                        json.dumps(tfidf_vector),
                    ),
                )

            conn.commit()
            conn.close()

            logger.info(f"构建了包含 {len(documents)} 个文档的关键词索引")

        except Exception as e:
            logger.error(f"构建关键词索引失败: {e}")

    def search(self, query: str, n_results: int = 10) -> List[Dict[str, Any]]:
        """关键词搜索"""
        try:
            if self.tfidf_matrix is None or len(self.documents) == 0:
                return []

            # 将查询转换为TF-IDF向量
            query_vector = self.tfidf_vectorizer.transform([query])

            # 计算相似度
            similarities = cosine_similarity(query_vector, self.tfidf_matrix).flatten()

            # 排序并返回top结果
            top_indices = np.argsort(similarities)[::-1][:n_results]

            results = []
            for idx in top_indices:
                if similarities[idx] > 0:  # 只返回有相关性的结果
                    results.append(
                        {
                            "id": self.documents[idx]["id"],
                            "content": self.documents[idx]["content"],
                            "metadata": self.documents[idx].get("metadata", {}),
                            "score": float(similarities[idx]),
                        }
                    )

            return results

        except Exception as e:
            logger.error(f"关键词搜索失败: {e}")
            return []


class EnhancedRAGRetriever(Retriever):
    """增强的RAG检索器 - 结合向量召回和关键词召回"""

    def __init__(
        self,
        repo_path: str,
        db_path: str = "temp/rag_data/enhanced_rag",
        embedding_config: Optional[Dict[str, Any]] = None,
    ):
        self.repo_path = repo_path
        self.db_path = db_path

        # 初始化基础代码检索器
        self.base_retriever = CodeRetriever(repo_path, f"{db_path}_base.db")

        # 初始化embedding客户端
        if embedding_config is None:
            embedding_config = load_embedding_config()
        self.embedding_client = EmbeddingClient(embedding_config)

        # 初始化存储
        self.vector_store = VectorStore(f"{db_path}_vectors")
        self.keyword_index = KeywordIndex(f"{db_path}_keywords.db")

        # 权重配置
        self.vector_weight = 0.6  # 向量召回权重
        self.keyword_weight = 0.4  # 关键词召回权重

        # 标记是否需要构建索引
        self._needs_indexing = False

        # 确保索引已构建
        self._ensure_indexed()

    def _ensure_indexed(self):
        """确保增强索引已构建"""
        try:
            vector_count = self.vector_store.count()
            if vector_count == 0:
                logger.info("向量存储为空，需要构建增强索引")
                # 标记需要构建索引，在第一次搜索时异步构建
                self._needs_indexing = True
            else:
                logger.info(f"增强索引已存在，包含 {vector_count} 个向量")
                self._needs_indexing = False
        except Exception as e:
            logger.error(f"检查增强索引状态失败: {e}")
            self._needs_indexing = True

    async def _build_enhanced_index(self):
        """构建增强索引"""
        try:
            # 获取所有代码块
            search_results = self.base_retriever.indexer.search_code("", limit=10000)

            if not search_results:
                logger.warning("没有找到代码块，跳过增强索引构建")
                return

            # 准备文档数据
            documents = []
            texts = []

            for result in search_results:
                doc_id = f"{result['file_path']}:{result.get('start_line', 0)}"
                content = result["content"]

                # 确保metadata中没有None值
                metadata = {
                    "file_path": str(result.get("file_path", "unknown")),
                    "language": str(result.get("language", "unknown")),
                    "chunk_type": str(result.get("chunk_type", "unknown")),
                    "name": str(result.get("name", "")),
                    "start_line": int(result.get("start_line", 0)),
                    "end_line": int(result.get("end_line", 0)),
                }

                documents.append(
                    {"id": doc_id, "content": content, "metadata": metadata}
                )
                texts.append(content)

            logger.info(f"准备为 {len(documents)} 个文档构建增强索引")

            # 获取embeddings（分批处理，DashScope限制为10个）
            batch_size = 10
            all_embeddings = []

            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i : i + batch_size]
                try:
                    batch_embeddings = await self.embedding_client.get_embeddings(
                        batch_texts
                    )
                    all_embeddings.extend(batch_embeddings)
                    logger.info(
                        f"处理了 {len(all_embeddings)}/{len(texts)} 个embeddings"
                    )
                except Exception as e:
                    logger.error(f"获取embeddings失败: {e}")
                    # 使用零向量作为fallback，使用配置的维度
                    dimensions = self.embedding_client.model_config.get(
                        "dimensions", 1024
                    )
                    batch_embeddings = [[0.0] * dimensions for _ in batch_texts]
                    all_embeddings.extend(batch_embeddings)

            # 构建向量存储
            self.vector_store.add_documents(documents, all_embeddings)

            # 构建关键词索引
            self.keyword_index.build_index(documents)

            logger.info("增强索引构建完成")

        except Exception as e:
            logger.error(f"构建增强索引失败: {e}")

    async def hybrid_search(
        self,
        query: str,
        n_results: int = 10,
        vector_weight: Optional[float] = None,
        keyword_weight: Optional[float] = None,
    ) -> List[RetrievalResult]:
        """混合搜索：结合向量召回和关键词召回"""
        vector_weight = vector_weight or self.vector_weight
        keyword_weight = keyword_weight or self.keyword_weight

        try:
            # 如果需要构建索引，先构建
            if self._needs_indexing:
                logger.info("首次搜索，开始构建增强索引...")
                await self._build_enhanced_index()
                self._needs_indexing = False

            # 1. 向量召回
            query_embedding = await self.embedding_client.get_embeddings([query])
            vector_results = self.vector_store.search(
                query_embedding[0], n_results=n_results * 2
            )

            # 2. 关键词召回
            keyword_results = self.keyword_index.search(query, n_results=n_results * 2)

            # 3. 合并和重排序
            combined_results = self._combine_results(
                vector_results, keyword_results, vector_weight, keyword_weight
            )

            # 4. 转换为RetrievalResult
            retrieval_results = []
            for result in combined_results[:n_results]:
                doc = self._create_document_from_result(result)
                retrieval_result = RetrievalResult(
                    document=doc,
                    vector_score=result.get("vector_score", 0.0),
                    keyword_score=result.get("keyword_score", 0.0),
                    combined_score=result["combined_score"],
                    retrieval_method="hybrid",
                )
                retrieval_results.append(retrieval_result)

            return retrieval_results

        except Exception as e:
            logger.error(f"混合搜索失败: {e}")
            return []

    def _combine_results(
        self,
        vector_results: List[Dict[str, Any]],
        keyword_results: List[Dict[str, Any]],
        vector_weight: float,
        keyword_weight: float,
    ) -> List[Dict[str, Any]]:
        """合并向量和关键词搜索结果"""
        # 创建结果字典
        all_results = {}

        # 处理向量结果
        for result in vector_results:
            doc_id = result["id"]
            # 将距离转换为相似度分数（距离越小，相似度越高）
            vector_score = max(0, 1.0 - result.get("distance", 1.0))

            all_results[doc_id] = {
                "id": doc_id,
                "content": result["content"],
                "metadata": result["metadata"],
                "vector_score": vector_score,
                "keyword_score": 0.0,
                "combined_score": vector_score * vector_weight,
            }

        # 处理关键词结果
        for result in keyword_results:
            doc_id = result["id"]
            keyword_score = result["score"]

            if doc_id in all_results:
                # 更新已存在的结果
                all_results[doc_id]["keyword_score"] = keyword_score
                all_results[doc_id]["combined_score"] = (
                    all_results[doc_id]["vector_score"] * vector_weight
                    + keyword_score * keyword_weight
                )
            else:
                # 添加新结果
                all_results[doc_id] = {
                    "id": doc_id,
                    "content": result["content"],
                    "metadata": result["metadata"],
                    "vector_score": 0.0,
                    "keyword_score": keyword_score,
                    "combined_score": keyword_score * keyword_weight,
                }

        # 按combined_score排序
        sorted_results = sorted(
            all_results.values(), key=lambda x: x["combined_score"], reverse=True
        )

        return sorted_results

    def _create_document_from_result(self, result: Dict[str, Any]) -> Document:
        """从搜索结果创建Document对象"""
        metadata = result.get("metadata", {})
        file_path = metadata.get("file_path", "unknown")

        chunk = Chunk(content=result["content"], similarity=result["combined_score"])

        document = Document(
            id=result["id"],
            url=f"file://{file_path}#{metadata.get('start_line', 0)}",
            title=f"{Path(file_path).name} - {metadata.get('name', 'Code Block')}",
            chunks=[chunk],
        )

        return document

    # 实现Retriever抽象方法
    def list_resources(self, query: str | None = None) -> List[Resource]:
        """列出代码资源"""
        return self.base_retriever.list_resources(query)

    def query_relevant_documents(
        self, query: str, resources: List[Resource] = []
    ) -> List[Document]:
        """查询相关文档 - 使用混合搜索"""
        try:
            # 运行异步混合搜索
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 如果在已有的事件循环中，使用线程池
                    import concurrent.futures

                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, self.hybrid_search(query))
                        retrieval_results = future.result(timeout=30)
                else:
                    retrieval_results = asyncio.run(self.hybrid_search(query))
            except:
                # 如果异步调用失败，回退到基础检索器
                logger.warning("异步混合搜索失败，回退到基础检索器")
                return self.base_retriever.query_relevant_documents(query, resources)

            # 转换为Document列表
            documents = [result.document for result in retrieval_results]

            logger.info(f"混合搜索返回了 {len(documents)} 个文档")
            return documents

        except Exception as e:
            logger.error(f"查询相关文档失败: {e}")
            # 回退到基础检索器
            return self.base_retriever.query_relevant_documents(query, resources)

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        try:
            base_stats = self.base_retriever.get_indexer_statistics()
            vector_count = self.vector_store.count()

            return {
                **base_stats,
                "vector_store_count": vector_count,
                "enhanced_indexing": vector_count > 0,
                "hybrid_search_enabled": True,
                "vector_weight": self.vector_weight,
                "keyword_weight": self.keyword_weight,
            }
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {"error": str(e)}
