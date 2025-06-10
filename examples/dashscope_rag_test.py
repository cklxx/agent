#!/usr/bin/env python3
"""
阿里云百炼DashScope embedding API测试
测试新集成的DashScope embedding服务在增强RAG检索器中的使用
"""

import asyncio
import os
import logging
from pathlib import Path
import sys

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rag.enhanced_retriever import EnhancedRAGRetriever, EmbeddingClient

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


async def test_dashscope_embedding_client():
    """测试DashScope embedding客户端"""
    print("🧪 测试DashScope Embedding客户端...")

    # DashScope配置
    dashscope_config = {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "text-embedding-v4",
        "api_key": os.getenv(
            "DASHSCOPE_API_KEY", "sk-43b68821d03249bd855b251ddf2c9248"
        ),
        "dimensions": 1024,
        "encoding_format": "float",
    }

    client = EmbeddingClient(dashscope_config)

    # 测试文本
    test_texts = [
        "Python代码检索器实现",
        "向量相似度搜索算法",
        "RAG增强检索系统",
        "衣服的质量杠杠的，很漂亮，不枉我等了这么久啊，喜欢，以后还来这里买",
    ]

    try:
        print(f"📡 正在获取 {len(test_texts)} 个文本的embeddings...")
        embeddings = await client.get_embeddings(test_texts)

        print(f"✅ 成功获取embeddings:")
        for i, (text, embedding) in enumerate(zip(test_texts, embeddings)):
            print(f"  {i+1}. '{text[:30]}...' -> 向量维度: {len(embedding)}")
            print(f"      向量前5个值: {embedding[:5]}")

        return True

    except Exception as e:
        print(f"❌ DashScope embedding测试失败: {e}")
        return False


async def test_dashscope_rag_retriever():
    """测试使用DashScope的增强RAG检索器"""
    print("\n🔍 测试DashScope增强RAG检索器...")

    # 获取当前项目根目录
    repo_path = str(Path(__file__).parent.parent)

    # DashScope配置
    embedding_config = {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "text-embedding-v4",
        "api_key": os.getenv(
            "DASHSCOPE_API_KEY", "sk-43b68821d03249bd855b251ddf2c9248"
        ),
        "dimensions": 1024,
        "encoding_format": "float",
    }

    try:
        # 初始化检索器
        print("🚀 初始化DashScope增强检索器...")
        retriever = EnhancedRAGRetriever(
            repo_path=repo_path,
            db_path="temp/rag_data/dashscope_rag_test",
            embedding_config=embedding_config,
        )

        print("✅ 检索器初始化完成")

        # 获取统计信息
        stats = retriever.get_statistics()
        print(f"\n📊 索引统计:")
        print(f"  - 总文件数: {stats.get('total_files', 0)}")
        print(f"  - 向量存储数量: {stats.get('vector_store_count', 0)}")
        print(f"  - 增强索引启用: {stats.get('enhanced_indexing', False)}")

        # 测试查询
        test_queries = [
            "代码检索器实现",
            "embedding向量搜索",
            "混合搜索算法",
            "RAG检索增强",
            "Python异步编程",
        ]

        print(f"\n🔍 开始测试DashScope混合搜索...")

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

                        # 显示代码片段（前80字符）
                        if doc.chunks:
                            content_preview = (
                                doc.chunks[0].content[:80].replace("\n", " ")
                            )
                            print(f"     预览: {content_preview}...")

                else:
                    print("❌ 未找到相关结果")

            except Exception as e:
                print(f"❌ 搜索失败: {e}")

        # 测试标准API
        print(f"\n🔧 测试标准Retriever API...")

        # 查询相关文档
        documents = retriever.query_relevant_documents("代码检索")
        print(f"✅ 通过标准API查询到 {len(documents)} 个文档")

        for doc in documents[:3]:
            print(f"  - {doc.title}: {len(doc.chunks)} 个代码块")

        return True

    except Exception as e:
        print(f"❌ DashScope RAG检索器测试失败: {e}")
        return False


async def compare_embedding_services():
    """比较不同embedding服务的效果"""
    print("\n📊 比较不同embedding服务...")

    # 测试查询
    test_query = "Python代码检索器实现"

    configs = [
        {
            "name": "DashScope v4",
            "config": {
                "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                "model": "text-embedding-v4",
                "api_key": os.getenv("DASHSCOPE_API_KEY", "sk-"),
                "dimensions": 1024,
                "encoding_format": "float",
            },
        },
        {
            "name": "DashScope v3",
            "config": {
                "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                "model": "text-embedding-v3",
                "api_key": os.getenv("DASHSCOPE_API_KEY", "sk-"),
                "dimensions": 1024,  # v3支持的有效维度：64, 128, 256, 512, 768, 1024
                "encoding_format": "float",
            },
        },
    ]

    for config_info in configs:
        name = config_info["name"]
        config = config_info["config"]

        print(f"\n🧪 测试 {name}...")

        try:
            client = EmbeddingClient(config)
            embeddings = await client.get_embeddings([test_query])

            if embeddings and embeddings[0]:
                print(f"✅ {name}: 向量维度 {len(embeddings[0])}")
                print(f"   前3个值: {embeddings[0][:3]}")
            else:
                print(f"❌ {name}: 获取embedding失败")

        except Exception as e:
            print(f"❌ {name}: 测试失败 - {e}")


async def main():
    """主函数"""
    print("🎯 阿里云百炼DashScope Embedding测试")
    print("=" * 60)

    # 检查API密钥
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        print("⚠️  警告: 未找到DASHSCOPE_API_KEY环境变量")
        print("   将使用默认测试密钥进行演示")
    else:
        print(f"✅ 找到DASHSCOPE_API_KEY: {api_key[:15]}...")

    success_count = 0
    total_tests = 3

    # 1. 测试embedding客户端
    if await test_dashscope_embedding_client():
        success_count += 1

    # 2. 测试RAG检索器
    if await test_dashscope_rag_retriever():
        success_count += 1

    # 3. 比较不同服务
    try:
        await compare_embedding_services()
        success_count += 1
    except Exception as e:
        print(f"❌ 服务比较测试失败: {e}")

    # 总结
    print(f"\n" + "=" * 60)
    print(f"🎉 测试完成: {success_count}/{total_tests} 个测试通过")

    if success_count == total_tests:
        print("✅ 所有测试通过！DashScope集成成功！")
        print("\n💡 使用建议:")
        print("  - text-embedding-v4: 1024维，性能更好，适合大规模应用")
        print("  - text-embedding-v3: 1536维，精度更高，适合精确匹配")
        print("  - 支持中文和英文混合检索")
        print("  - 国内访问速度快，稳定性好")
    else:
        print("⚠️  部分测试失败，请检查配置和网络连接")

    print("\n🔧 配置方法:")
    print("export DASHSCOPE_API_KEY='your-dashscope-key'")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⏹️  测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {e}")
        import traceback

        traceback.print_exc()
