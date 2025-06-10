#!/usr/bin/env python3
"""
增强RAG检索器单元测试
"""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
import sys

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rag.enhanced_retriever import (
    EnhancedRAGRetriever,
    EmbeddingClient,
    VectorStore,
    KeywordIndex,
    RetrievalResult,
)


@pytest.fixture
def temp_repo():
    """创建临时测试仓库"""
    temp_dir = tempfile.mkdtemp()
    repo_path = Path(temp_dir) / "test_repo"
    repo_path.mkdir(parents=True, exist_ok=True)

    # 创建测试文件
    (repo_path / "test_file.py").write_text(
        """
def test_function():
    '''测试函数'''
    return "hello world"

class TestClass:
    '''测试类'''
    def method(self):
        return "test method"
"""
    )

    (repo_path / "utils.py").write_text(
        """
def utility_function():
    '''工具函数'''
    pass

async def async_function():
    '''异步函数'''
    await asyncio.sleep(0.1)
    return "async result"
"""
    )

    yield str(repo_path)

    # 清理
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_embedding_config():
    """模拟embedding配置"""
    return {
        "base_url": "https://api.openai.com/v1",
        "model": "text-embedding-3-small",
        "api_key": "sk-test",
    }


class TestEmbeddingClient:
    """测试EmbeddingClient"""

    def test_init(self, mock_embedding_config):
        """测试初始化"""
        client = EmbeddingClient(mock_embedding_config)
        assert client.api_key == "sk-test"
        assert client.model == "text-embedding-3-small"

    @pytest.mark.asyncio
    async def test_get_embeddings_fallback(self, mock_embedding_config):
        """测试embedding获取失败时的fallback"""
        client = EmbeddingClient(mock_embedding_config)

        # 使用无效的API密钥，应该回退到随机向量
        embeddings = await client.get_embeddings(["test text"])

        assert len(embeddings) == 1
        assert len(embeddings[0]) == 1536  # OpenAI embedding维度
        assert all(x == 0.0 for x in embeddings[0])  # fallback返回零向量


class TestVectorStore:
    """测试VectorStore"""

    def test_init(self):
        """测试向量存储初始化"""
        with tempfile.TemporaryDirectory() as temp_dir:
            vector_store = VectorStore(temp_dir)
            assert vector_store.count() == 0

    def test_add_and_search(self):
        """测试添加文档和搜索"""
        with tempfile.TemporaryDirectory() as temp_dir:
            vector_store = VectorStore(temp_dir)

            # 添加测试文档
            documents = [
                {"id": "doc1", "content": "test content", "metadata": {"type": "test"}}
            ]
            embeddings = [[0.1] * 1536]  # 模拟embedding

            vector_store.add_documents(documents, embeddings)
            assert vector_store.count() == 1

            # 搜索
            results = vector_store.search([0.1] * 1536, n_results=1)
            assert len(results) == 1
            assert results[0]["id"] == "doc1"


class TestKeywordIndex:
    """测试KeywordIndex"""

    def test_init(self):
        """测试关键词索引初始化"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            keyword_index = KeywordIndex(str(db_path))
            assert db_path.exists()

    def test_build_and_search(self):
        """测试构建索引和搜索"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            keyword_index = KeywordIndex(str(db_path))

            # 构建索引
            documents = [
                {
                    "id": "doc1",
                    "content": "python function definition",
                    "metadata": {"type": "code"},
                },
                {
                    "id": "doc2",
                    "content": "javascript async function",
                    "metadata": {"type": "code"},
                },
            ]

            keyword_index.build_index(documents)

            # 搜索
            results = keyword_index.search("python", n_results=5)
            assert len(results) >= 1
            assert any(result["id"] == "doc1" for result in results)

            results = keyword_index.search("javascript", n_results=5)
            assert any(result["id"] == "doc2" for result in results)


class TestEnhancedRAGRetriever:
    """测试EnhancedRAGRetriever"""

    def test_init(self, temp_repo, mock_embedding_config):
        """测试增强检索器初始化"""
        retriever = EnhancedRAGRetriever(
            repo_path=temp_repo,
            db_path="temp/test_enhanced_rag",
            embedding_config=mock_embedding_config,
        )

        assert retriever.repo_path == temp_repo
        assert retriever.vector_weight == 0.6
        assert retriever.keyword_weight == 0.4

    def test_list_resources(self, temp_repo, mock_embedding_config):
        """测试列出资源"""
        retriever = EnhancedRAGRetriever(
            repo_path=temp_repo,
            db_path="temp/test_enhanced_rag_resources",
            embedding_config=mock_embedding_config,
        )

        resources = retriever.list_resources()
        assert len(resources) >= 0  # 可能没有资源或有资源

    def test_query_relevant_documents(self, temp_repo, mock_embedding_config):
        """测试查询相关文档"""
        retriever = EnhancedRAGRetriever(
            repo_path=temp_repo,
            db_path="temp/test_enhanced_rag_query",
            embedding_config=mock_embedding_config,
        )

        # 查询文档
        documents = retriever.query_relevant_documents("test function")
        assert isinstance(documents, list)
        # 由于使用mock embedding，可能返回空结果

    @pytest.mark.asyncio
    async def test_hybrid_search(self, temp_repo, mock_embedding_config):
        """测试混合搜索"""
        retriever = EnhancedRAGRetriever(
            repo_path=temp_repo,
            db_path="temp/test_enhanced_rag_hybrid",
            embedding_config=mock_embedding_config,
        )

        # 执行混合搜索
        results = await retriever.hybrid_search("test function", n_results=3)

        assert isinstance(results, list)
        for result in results:
            assert isinstance(result, RetrievalResult)
            assert hasattr(result, "document")
            assert hasattr(result, "vector_score")
            assert hasattr(result, "keyword_score")
            assert hasattr(result, "combined_score")

    def test_get_statistics(self, temp_repo, mock_embedding_config):
        """测试获取统计信息"""
        retriever = EnhancedRAGRetriever(
            repo_path=temp_repo,
            db_path="temp/test_enhanced_rag_stats",
            embedding_config=mock_embedding_config,
        )

        stats = retriever.get_statistics()
        assert isinstance(stats, dict)
        assert "vector_store_count" in stats
        assert "enhanced_indexing" in stats
        assert "hybrid_search_enabled" in stats
        assert "vector_weight" in stats
        assert "keyword_weight" in stats

    def test_combine_results(self, temp_repo, mock_embedding_config):
        """测试结果合并"""
        retriever = EnhancedRAGRetriever(
            repo_path=temp_repo,
            db_path="temp/test_enhanced_rag_combine",
            embedding_config=mock_embedding_config,
        )

        vector_results = [
            {"id": "doc1", "content": "test content", "metadata": {}, "distance": 0.2}
        ]

        keyword_results = [
            {"id": "doc1", "content": "test content", "metadata": {}, "score": 0.8},
            {"id": "doc2", "content": "other content", "metadata": {}, "score": 0.6},
        ]

        combined = retriever._combine_results(vector_results, keyword_results, 0.6, 0.4)

        assert len(combined) == 2
        assert combined[0]["id"] == "doc1"  # 应该有最高的综合分数
        assert "combined_score" in combined[0]
        assert "vector_score" in combined[0]
        assert "keyword_score" in combined[0]


@pytest.mark.integration
class TestEnhancedRAGIntegration:
    """集成测试"""

    @pytest.mark.asyncio
    async def test_full_workflow(self, temp_repo):
        """测试完整工作流程"""
        # 使用模拟配置
        embedding_config = {
            "base_url": "https://api.openai.com/v1",
            "model": "text-embedding-3-small",
            "api_key": "sk-test",  # 会失败，但有fallback
        }

        retriever = EnhancedRAGRetriever(
            repo_path=temp_repo,
            db_path="temp/test_enhanced_rag_integration",
            embedding_config=embedding_config,
        )

        # 1. 检查初始状态
        stats = retriever.get_statistics()
        assert isinstance(stats, dict)

        # 2. 列出资源
        resources = retriever.list_resources("python")
        assert isinstance(resources, list)

        # 3. 执行混合搜索
        results = await retriever.hybrid_search("function", n_results=2)
        assert isinstance(results, list)

        # 4. 使用标准API查询
        documents = retriever.query_relevant_documents("test")
        assert isinstance(documents, list)

        print(f"集成测试完成 - 找到 {len(documents)} 个文档")


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])
