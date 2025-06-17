#!/usr/bin/env python3
"""
快速DashScope测试 - 只处理少量文档
验证修复后的batch size和metadata问题
"""

import asyncio
import os
import sys
from pathlib import Path

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rag.enhanced_retriever import EnhancedRAGRetriever


async def quick_dashscope_test():
    """快速DashScope测试"""
    print("🚀 DashScope 快速测试")
    print("=" * 40)

    # 获取当前项目根目录
    repo_path = str(Path(__file__).parent.parent)

    # DashScope配置
    embedding_config = {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "text-embedding-v4",
        "api_key": os.getenv("DASHSCOPE_API_KEY", "sk-xxx"),
        "dimensions": 1024,
        "encoding_format": "float",
    }

    try:
        # 初始化检索器（使用新的路径避免冲突）
        print("🔧 初始化增强检索器...")
        retriever = EnhancedRAGRetriever(
            repo_path=repo_path,
            db_path="temp/rag_data/quick_test",
            embedding_config=embedding_config,
        )

        print("✅ 检索器初始化完成")

        # 测试查询
        test_queries = ["Python代码", "RAG检索"]

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
                        print(f"     向量得分: {result.vector_score:.3f}")
                        print(f"     关键词得分: {result.keyword_score:.3f}")
                        print(f"     综合得分: {result.combined_score:.3f}")

                else:
                    print("❌ 未找到相关结果")

            except Exception as e:
                print(f"❌ 搜索失败: {e}")
                import traceback

                traceback.print_exc()

        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """主函数"""
    # 检查API密钥
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if api_key:
        print(f"✅ 找到API密钥: {api_key[:15]}...")
    else:
        print("⚠️  未找到DASHSCOPE_API_KEY环境变量")

    # 运行测试
    success = await quick_dashscope_test()

    if success:
        print(f"\n🎉 快速测试成功！")
    else:
        print(f"\n❌ 测试失败")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️  测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {e}")
