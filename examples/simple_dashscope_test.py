#!/usr/bin/env python3
"""
简化的DashScope embedding API测试
专注于测试API基本功能
"""

import asyncio
import os
import sys
from pathlib import Path

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rag.enhanced_retriever import EmbeddingClient


async def test_dashscope_basic():
    """基础DashScope embedding测试"""
    print("🧪 DashScope Embedding 基础测试")
    print("=" * 50)

    # 测试配置
    configs = [
        {
            "name": "DashScope v4",
            "config": {
                "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                "model": "text-embedding-v4",
                "api_key": os.getenv(
                    "DASHSCOPE_API_KEY", "sk-43b68821d03249bd855b251ddf2c9248"
                ),
                "dimensions": 1024,
                "encoding_format": "float",
            },
        },
        {
            "name": "DashScope v3",
            "config": {
                "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                "model": "text-embedding-v3",
                "api_key": os.getenv(
                    "DASHSCOPE_API_KEY", "sk-43b68821d03249bd855b251ddf2c9248"
                ),
                "dimensions": 1024,
                "encoding_format": "float",
            },
        },
    ]

    # 测试文本
    test_texts = [
        "Python代码检索器实现",
        "向量相似度搜索算法",
        "RAG增强检索系统",
        "机器学习模型训练",
        "深度学习神经网络",
    ]

    success_count = 0

    for config_info in configs:
        name = config_info["name"]
        config = config_info["config"]

        print(f"\n🔍 测试 {name}...")
        print(f"   模型: {config['model']}")
        print(f"   维度: {config['dimensions']}")

        try:
            # 创建客户端
            client = EmbeddingClient(config)

            # 单个文本测试
            print(f"   📝 单个文本测试...")
            single_embedding = await client.get_embeddings([test_texts[0]])

            if single_embedding and single_embedding[0]:
                print(f"   ✅ 单个文本成功 - 维度: {len(single_embedding[0])}")
                print(f"      前3个值: {single_embedding[0][:3]}")
            else:
                print(f"   ❌ 单个文本失败")
                continue

            # 批量文本测试
            print(f"   📚 批量文本测试 ({len(test_texts)} 个文本)...")
            batch_embeddings = await client.get_embeddings(test_texts)

            if batch_embeddings and len(batch_embeddings) == len(test_texts):
                print(f"   ✅ 批量文本成功 - 返回 {len(batch_embeddings)} 个向量")

                # 计算向量相似度示例
                if len(batch_embeddings) >= 2:
                    import numpy as np

                    vec1 = np.array(batch_embeddings[0])
                    vec2 = np.array(batch_embeddings[1])
                    similarity = np.dot(vec1, vec2) / (
                        np.linalg.norm(vec1) * np.linalg.norm(vec2)
                    )
                    print(
                        f"      '{test_texts[0]}' 与 '{test_texts[1]}' 相似度: {similarity:.3f}"
                    )

                success_count += 1

            else:
                print(
                    f"   ❌ 批量文本失败 - 期望 {len(test_texts)} 个，实际 {len(batch_embeddings) if batch_embeddings else 0} 个"
                )

        except Exception as e:
            print(f"   ❌ {name} 测试失败: {e}")

    # 测试总结
    print(f"\n" + "=" * 50)
    print(f"🎉 测试完成: {success_count}/{len(configs)} 个模型通过")

    if success_count > 0:
        print("✅ DashScope embedding API 工作正常！")
        print("\n💡 推荐使用:")
        print("  - text-embedding-v4: 最新模型，性能优化")
        print("  - dimensions=1024: 平衡性能和精度")
        print("  - 支持中英文混合检索")
    else:
        print("❌ 所有测试失败，请检查API密钥和网络连接")

    return success_count > 0


async def test_similarity_search():
    """测试向量相似度搜索"""
    print("\n🔍 向量相似度搜索测试")
    print("-" * 30)

    config = {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "text-embedding-v4",
        "api_key": os.getenv(
            "DASHSCOPE_API_KEY", "sk-43b68821d03249bd855b251ddf2c9248"
        ),
        "dimensions": 1024,
        "encoding_format": "float",
    }

    # 代码相关的文本集合
    code_texts = [
        "Python异步编程实现",
        "RAG检索增强生成",
        "向量数据库存储",
        "机器学习模型训练",
        "深度学习神经网络",
        "代码索引和搜索",
        "embedding向量生成",
        "自然语言处理",
    ]

    query = "代码检索和搜索功能"

    try:
        client = EmbeddingClient(config)

        # 获取查询向量
        query_embedding = await client.get_embeddings([query])

        # 获取文档向量
        doc_embeddings = await client.get_embeddings(code_texts)

        if query_embedding and doc_embeddings:
            import numpy as np

            query_vec = np.array(query_embedding[0])

            # 计算相似度
            similarities = []
            for i, doc_embedding in enumerate(doc_embeddings):
                doc_vec = np.array(doc_embedding)
                similarity = np.dot(query_vec, doc_vec) / (
                    np.linalg.norm(query_vec) * np.linalg.norm(doc_vec)
                )
                similarities.append((similarity, code_texts[i]))

            # 按相似度排序
            similarities.sort(reverse=True)

            print(f"查询: '{query}'")
            print("最相关的文档:")

            for i, (score, text) in enumerate(similarities[:5], 1):
                print(f"  {i}. {text} (相似度: {score:.3f})")

            return True

    except Exception as e:
        print(f"❌ 相似度搜索测试失败: {e}")
        return False


async def main():
    """主函数"""
    # 检查API密钥
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if api_key:
        print(f"✅ 找到API密钥: {api_key[:15]}...")
    else:
        print("⚠️  未找到DASHSCOPE_API_KEY环境变量")
        print("使用默认测试密钥")

    # 基础测试
    basic_success = await test_dashscope_basic()

    # 相似度搜索测试
    if basic_success:
        await test_similarity_search()

    print(f"\n🔧 设置环境变量:")
    print("export DASHSCOPE_API_KEY='your-api-key'")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️  测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {e}")
