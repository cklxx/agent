#!/usr/bin/env python3
"""
增强RAG检索器演示
展示结合向量相似度和关键词召回的混合搜索功能
"""

import asyncio
import os
import logging
from pathlib import Path
import sys

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rag.enhanced_retriever import EnhancedRAGRetriever

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


async def demonstrate_enhanced_rag():
    """演示增强RAG检索器的功能"""

    # 获取当前项目根目录
    repo_path = str(Path(__file__).parent.parent)

    print("🚀 初始化增强RAG检索器...")
    print(f"Repository路径: {repo_path}")

    # 配置embedding服务（支持多种API）
    embedding_configs = [
        {
            "name": "阿里云百炼DashScope (推荐)",
            "config": {
                "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                "model": "text-embedding-v4",
                "api_key": os.getenv("DASHSCOPE_API_KEY", "sk-test"),
                "dimensions": 1024,
                "encoding_format": "float",
            },
        },
        {
            "name": "OpenAI (如果可用)",
            "config": {
                "base_url": "https://api.openai.com/v1",
                "model": "text-embedding-3-small",
                "api_key": os.getenv("OPENAI_API_KEY", "sk-test"),
            },
        },
        {
            "name": "OpenRouter (备用)",
            "config": {
                "base_url": "https://openrouter.ai/api/v1",
                "model": "openai/text-embedding-3-small",
                "api_key": os.getenv("OPENROUTER_API_KEY", "sk-or-test"),
            },
        },
    ]

    # 尝试使用第一个可用的配置
    embedding_config = embedding_configs[0]["config"]

    try:
        # 初始化增强检索器
        retriever = EnhancedRAGRetriever(
            repo_path=repo_path,
            db_path="temp/rag_data/enhanced_rag_demo",
            embedding_config=embedding_config,
        )

        print("✅ 增强RAG检索器初始化完成")

        # 获取统计信息
        stats = retriever.get_statistics()
        print(f"\n📊 索引统计:")
        print(f"  - 总文件数: {stats.get('total_files', 0)}")
        print(f"  - 向量存储数量: {stats.get('vector_store_count', 0)}")
        print(f"  - 增强索引启用: {stats.get('enhanced_indexing', False)}")
        print(f"  - 混合搜索启用: {stats.get('hybrid_search_enabled', False)}")
        print(f"  - 向量权重: {stats.get('vector_weight', 0)}")
        print(f"  - 关键词权重: {stats.get('keyword_weight', 0)}")

        # 测试查询
        test_queries = [
            "代码检索器",
            "embedding api",
            "向量相似度搜索",
            "混合搜索算法",
            "RAG增强",
            "async function",
            "class definition",
            "error handling",
        ]

        print(f"\n🔍 开始测试混合搜索...")

        for i, query in enumerate(test_queries, 1):
            print(f"\n--- 查询 {i}: '{query}' ---")

            try:
                # 执行混合搜索
                results = await retriever.hybrid_search(query, n_results=3)

                if results:
                    print(f"✅ 找到 {len(results)} 个相关结果:")

                    for j, result in enumerate(results, 1):
                        doc = result.document
                        print(f"\n  {j}. {doc.title}")
                        print(f"     文件: {doc.id}")
                        print(f"     向量得分: {result.vector_score:.3f}")
                        print(f"     关键词得分: {result.keyword_score:.3f}")
                        print(f"     综合得分: {result.combined_score:.3f}")
                        print(f"     检索方法: {result.retrieval_method}")

                        # 显示代码片段（前100字符）
                        if doc.chunks:
                            content_preview = (
                                doc.chunks[0].content[:100].replace("\n", " ")
                            )
                            print(f"     预览: {content_preview}...")

                else:
                    print("❌ 未找到相关结果")

            except Exception as e:
                print(f"❌ 搜索失败: {e}")

        # 测试标准API
        print(f"\n🔧 测试标准Retriever API...")

        # 列出资源
        resources = retriever.list_resources("python")
        print(f"✅ 找到 {len(resources)} 个资源")

        # 查询相关文档
        documents = retriever.query_relevant_documents("代码检索", resources[:2])
        print(f"✅ 通过标准API查询到 {len(documents)} 个文档")

        for doc in documents[:2]:
            print(f"  - {doc.title}: {len(doc.chunks)} 个代码块")

        print(f"\n🎉 增强RAG检索器演示完成!")
        print(f"\n💡 主要特性:")
        print(f"  ✓ 结合向量相似度和关键词召回")
        print(f"  ✓ 支持多种embedding API")
        print(f"  ✓ 自动索引构建和管理")
        print(f"  ✓ 可配置的权重调整")
        print(f"  ✓ 完全异步支持")
        print(f"  ✓ 兼容标准Retriever接口")

    except Exception as e:
        logger.error(f"演示过程中出现错误: {e}")
        print(f"❌ 演示失败: {e}")


def test_sync_api():
    """测试同步API"""
    print("\n🔧 测试同步API...")

    repo_path = str(Path(__file__).parent.parent)

    try:
        retriever = EnhancedRAGRetriever(
            repo_path=repo_path, db_path="temp/rag_data/enhanced_rag_sync_test"
        )

        # 使用同步API查询
        documents = retriever.query_relevant_documents("检索器")
        print(f"✅ 同步查询到 {len(documents)} 个文档")

        for doc in documents[:2]:
            print(f"  - {doc.title}")

    except Exception as e:
        print(f"❌ 同步API测试失败: {e}")


if __name__ == "__main__":
    print("🎯 增强RAG检索器演示")
    print("=" * 50)

    # 运行异步演示
    try:
        asyncio.run(demonstrate_enhanced_rag())
    except KeyboardInterrupt:
        print("\n\n⏹️  演示被用户中断")
    except Exception as e:
        print(f"\n❌ 异步演示失败: {e}")

    # 测试同步API
    test_sync_api()

    print("\n" + "=" * 50)
    print("演示结束")
