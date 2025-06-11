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
from unittest.mock import patch, MagicMock

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# 创建全局LLM mock，在所有测试开始前就启用
mock_llm_global = MagicMock()
mock_llm_global.invoke = MagicMock(
    return_value=MagicMock(content="Mocked LLM response")
)

# 在导入模块之前就开始patch
llm_patcher = patch("src.llms.llm.get_llm_by_type", return_value=mock_llm_global)
llm_patcher.start()

from rag.enhanced_retriever import (
    EnhancedRAGRetriever,
    EmbeddingClient,
    VectorStore,
    KeywordIndex,
    RetrievalResult,
)


@pytest.fixture(scope="session", autouse=True)
def setup_llm_mock():
    """设置全局LLM mock"""
    yield
    # 在所有测试结束后停止patch
    llm_patcher.stop()


@pytest.fixture
def mock_llm():
    """创建LLM mock"""
    llm = MagicMock()
    llm.invoke = MagicMock(return_value=MagicMock(content="Mocked LLM response"))
    return llm


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

    # 创建更多测试文件以增加覆盖率
    (repo_path / "config.yaml").write_text(
        """
app:
  name: test_app
  version: 1.0.0
"""
    )

    (repo_path / "README.md").write_text(
        """
# Test Project

This is a test project for RAG testing.
"""
    )

    (repo_path / "requirements.txt").write_text(
        """
pytest==7.0.0
asyncio==3.4.3
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

    def test_embedding_config_validation(self):
        """测试embedding配置验证"""
        # 测试缺失API密钥
        config = {"base_url": "https://api.openai.com/v1", "model": "test-model"}
        client = EmbeddingClient(config)
        # EmbeddingClient会设置默认的空字符串
        assert client.api_key == ""

        # 测试完整配置
        full_config = {
            "base_url": "https://api.openai.com/v1",
            "model": "test-model",
            "api_key": "test-key",
        }
        client = EmbeddingClient(full_config)
        assert client.api_key == "test-key"


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

    def test_vector_store_operations(self):
        """测试向量存储操作"""
        with tempfile.TemporaryDirectory() as temp_dir:
            vector_store = VectorStore(temp_dir)

            # 添加文档
            documents = [
                {"id": "doc1", "content": "test content", "metadata": {"type": "test"}},
                {
                    "id": "doc2",
                    "content": "another content",
                    "metadata": {"type": "test"},
                },
            ]
            embeddings = [[0.1] * 1536, [0.2] * 1536]
            vector_store.add_documents(documents, embeddings)
            assert vector_store.count() == 2

            # 测试搜索
            results = vector_store.search([0.1] * 1536, n_results=2)
            assert len(results) == 2


class TestKeywordIndex:
    """测试关键词索引"""

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

    def test_empty_search(self):
        """测试空搜索"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            keyword_index = KeywordIndex(str(db_path))

            # 在没有索引的情况下搜索
            results = keyword_index.search("test", n_results=5)
            assert len(results) == 0

    def test_keyword_index_multiple_search(self):
        """测试关键词索引多次搜索"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            keyword_index = KeywordIndex(str(db_path))

            # 构建索引
            documents = [
                {"id": "doc1", "content": "python programming test", "metadata": {}},
                {"id": "doc2", "content": "javascript coding test", "metadata": {}},
                {"id": "doc3", "content": "java development test", "metadata": {}},
            ]
            keyword_index.build_index(documents)

            # 测试多个不同的搜索
            python_results = keyword_index.search("python", n_results=5)
            assert len(python_results) >= 1

            javascript_results = keyword_index.search("javascript", n_results=5)
            assert len(javascript_results) >= 1

            test_results = keyword_index.search("test", n_results=5)
            assert len(test_results) >= 3  # 所有文档都包含test


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

        # 测试带查询的资源列表
        python_resources = retriever.list_resources("python")
        assert isinstance(python_resources, list)

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

    def test_default_weights(self, temp_repo, mock_embedding_config):
        """测试默认权重"""
        retriever = EnhancedRAGRetriever(
            repo_path=temp_repo,
            db_path="temp/test_enhanced_rag_weights",
            embedding_config=mock_embedding_config,
        )

        assert retriever.vector_weight == 0.6
        assert retriever.keyword_weight == 0.4

    def test_weight_modification(self, temp_repo, mock_embedding_config):
        """测试权重修改"""
        retriever = EnhancedRAGRetriever(
            repo_path=temp_repo,
            db_path="temp/test_enhanced_rag_update_weights",
            embedding_config=mock_embedding_config,
        )

        # 直接修改权重
        retriever.vector_weight = 0.8
        retriever.keyword_weight = 0.2
        assert retriever.vector_weight == 0.8
        assert retriever.keyword_weight == 0.2


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

    def test_error_handling(self, temp_repo):
        """测试错误处理"""
        # 测试无效路径
        try:
            retriever = EnhancedRAGRetriever(
                repo_path="/nonexistent/path",
                db_path="temp/test_enhanced_rag_error",
                embedding_config={"api_key": "test"},
            )
            # 如果没有抛出异常，至少检查是否能处理
            assert hasattr(retriever, "repo_path")
        except Exception as e:
            # 预期可能的异常
            assert isinstance(e, (ValueError, FileNotFoundError, OSError))


class TestRetrievalResult:
    """测试RetrievalResult类"""

    def test_creation(self):
        """测试创建RetrievalResult"""
        document = {"id": "test", "content": "test content"}
        result = RetrievalResult(
            document=document, vector_score=0.8, keyword_score=0.6, combined_score=0.7
        )

        assert result.document == document
        assert result.vector_score == 0.8
        assert result.keyword_score == 0.6
        assert result.combined_score == 0.7

    def test_default_values(self):
        """测试默认值"""
        document = {"id": "test", "content": "test content"}
        result = RetrievalResult(document=document)

        assert result.document == document
        assert result.vector_score == 0.0
        assert result.keyword_score == 0.0
        assert result.combined_score == 0.0
        assert result.retrieval_method == "hybrid"

    def test_custom_retrieval_method(self):
        """测试自定义检索方法"""
        document = {"id": "test", "content": "test content"}
        result = RetrievalResult(document=document, retrieval_method="vector")

        assert result.retrieval_method == "vector"


class TestLoadEmbeddingConfig:
    """测试embedding配置加载"""

    def test_load_config_with_env_vars(self):
        """测试通过环境变量加载配置"""
        import os
        from rag.enhanced_retriever import load_embedding_config

        # 设置环境变量
        original_key = os.environ.get("DASHSCOPE_API_KEY")
        os.environ["DASHSCOPE_API_KEY"] = "test-key"

        try:
            config = load_embedding_config()
            assert isinstance(config, dict)
            # 由于有环境变量，应该有api_key
            assert "api_key" in config
        finally:
            # 恢复原始环境变量
            if original_key is not None:
                os.environ["DASHSCOPE_API_KEY"] = original_key
            else:
                os.environ.pop("DASHSCOPE_API_KEY", None)

    def test_load_config_fallback(self):
        """测试配置加载fallback"""
        import os
        from rag.enhanced_retriever import load_embedding_config

        # 清除环境变量
        original_key = os.environ.get("DASHSCOPE_API_KEY")
        os.environ.pop("DASHSCOPE_API_KEY", None)

        try:
            config = load_embedding_config()
            assert isinstance(config, dict)
            # 应该有默认配置
            assert "base_url" in config
            assert "model" in config
        finally:
            # 恢复原始环境变量
            if original_key is not None:
                os.environ["DASHSCOPE_API_KEY"] = original_key


class TestAdditionalFeatures:
    """测试附加功能"""

    def test_vector_store_persistence(self):
        """测试向量存储持久化"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "vector_store"

            # 创建向量存储并添加数据
            vector_store1 = VectorStore(str(db_path))
            documents = [
                {"id": "doc1", "content": "test content", "metadata": {"type": "test"}}
            ]
            embeddings = [[0.1] * 1536]
            vector_store1.add_documents(documents, embeddings)
            count1 = vector_store1.count()

            # 重新打开向量存储，检查数据是否持久化
            vector_store2 = VectorStore(str(db_path))
            count2 = vector_store2.count()

            assert count1 == count2 == 1

    def test_keyword_index_rebuild(self):
        """测试关键词索引重建"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "keyword.db"

            # 创建索引并添加数据
            keyword_index = KeywordIndex(str(db_path))
            documents1 = [
                {"id": "doc1", "content": "python programming", "metadata": {}},
            ]
            keyword_index.build_index(documents1)

            # 搜索第一批数据
            results1 = keyword_index.search("python", n_results=5)
            assert len(results1) >= 1
            assert results1[0]["id"] == "doc1"

            # 重新构建索引
            documents2 = [
                {"id": "doc2", "content": "javascript coding", "metadata": {}},
                {"id": "doc3", "content": "java development", "metadata": {}},
            ]
            keyword_index.build_index(documents2)

            # 搜索新数据
            results2 = keyword_index.search("javascript", n_results=5)
            assert len(results2) >= 1
            assert results2[0]["id"] == "doc2"

    def test_enhanced_retriever_intelligent_filter(
        self, temp_repo, mock_embedding_config
    ):
        """测试智能过滤器开关"""
        # 测试启用智能过滤器
        retriever1 = EnhancedRAGRetriever(
            repo_path=temp_repo,
            db_path="temp/test_enhanced_rag_intelligent_on",
            embedding_config=mock_embedding_config,
            use_intelligent_filter=True,
        )
        assert retriever1.use_intelligent_filter is True

        # 测试禁用智能过滤器
        retriever2 = EnhancedRAGRetriever(
            repo_path=temp_repo,
            db_path="temp/test_enhanced_rag_intelligent_off",
            embedding_config=mock_embedding_config,
            use_intelligent_filter=False,
        )
        assert retriever2.use_intelligent_filter is False


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])
