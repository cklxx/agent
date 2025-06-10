#!/usr/bin/env python3
"""
代码RAG功能完整演示脚本

展示如何使用CodeRAGAdapter进行代码搜索和上下文增强
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.context.manager import ContextManager
from src.context.code_rag_adapter import CodeRAGAdapter
from src.context.base import ContextType


async def demo_basic_search():
    """演示基本搜索功能"""
    print("🔍 演示 1: 基本代码搜索")
    print("=" * 50)

    # 初始化
    context_manager = ContextManager(working_memory_limit=50)
    code_rag = CodeRAGAdapter(
        context_manager=context_manager,
        repo_path=".",
        db_path="temp/rag_data/demo_code_index.db",
    )

    # 搜索与"context"相关的代码
    search_queries = ["context", "ContextManager", "async def", "class"]

    for query in search_queries:
        print(f"\n🔎 搜索: '{query}'")
        context_ids = await code_rag.enhance_context_with_code(query, max_results=3)

        if context_ids:
            for i, context_id in enumerate(context_ids, 1):
                context = await context_manager.get_context(context_id)
                if context:
                    file_path = context.metadata.get("file_path", "unknown")
                    language = context.metadata.get("language", "unknown")
                    print(f"   {i}. {Path(file_path).name} ({language})")
                    # 显示部分内容
                    content_preview = (
                        context.content[:100] + "..."
                        if len(context.content) > 100
                        else context.content
                    )
                    print(f"      内容预览: {content_preview}")
        else:
            print("   未找到相关代码")

    return code_rag, context_manager


async def demo_function_class_search(code_rag, context_manager):
    """演示函数和类搜索"""
    print("\n\n🔧 演示 2: 函数和类搜索")
    print("=" * 50)

    # 搜索特定函数
    functions = ["__init__", "search", "add_context"]
    for func_name in functions:
        print(f"\n🔧 搜索函数: {func_name}")
        context_ids = await code_rag.search_and_add_function_context(func_name)

        if context_ids:
            for i, context_id in enumerate(context_ids, 1):
                context = await context_manager.get_context(context_id)
                if context:
                    file_path = context.metadata.get("file_path", "unknown")
                    print(f"   {i}. {func_name}() 在 {Path(file_path).name}")
        else:
            print(f"   未找到函数 {func_name}")

    # 搜索特定类
    classes = ["ContextManager", "CodeIndexer", "CodeRetriever"]
    for class_name in classes:
        print(f"\n🏗️ 搜索类: {class_name}")
        context_ids = await code_rag.search_and_add_class_context(class_name)

        if context_ids:
            for i, context_id in enumerate(context_ids, 1):
                context = await context_manager.get_context(context_id)
                if context:
                    file_path = context.metadata.get("file_path", "unknown")
                    print(f"   {i}. class {class_name} 在 {Path(file_path).name}")
        else:
            print(f"   未找到类 {class_name}")


async def demo_auto_enhancement(code_rag):
    """演示自动增强功能"""
    print("\n\n🤖 演示 3: 自动增强功能")
    print("=" * 50)

    queries = [
        "如何使用ContextManager?",
        "代码索引是如何工作的?",
        "搜索功能的实现原理",
        "异步编程相关代码",
    ]

    for query in queries:
        print(f"\n🤖 查询: '{query}'")
        result = await code_rag.auto_enhance_code_context(query)

        print(f"   增强了 {len(result['enhanced_contexts'])} 个context")
        if result["suggestions"]:
            print("   AI建议:")
            for suggestion in result["suggestions"]:
                print(f"     - {suggestion}")


async def demo_context_management(code_rag, context_manager):
    """演示context管理功能"""
    print("\n\n📋 演示 4: Context管理")
    print("=" * 50)

    # 显示当前所有代码context
    print("\n📋 当前代码context:")
    contexts = await context_manager.search_contexts(
        query="", context_type=ContextType.CODE, limit=10
    )

    if contexts:
        for i, context in enumerate(contexts, 1):
            file_path = context.metadata.get("file_path", "unknown")
            context_type = context.metadata.get("type", "unknown")
            source = context.metadata.get("source", "unknown")

            print(f"   {i}. {Path(file_path).name} ({context_type}, 来源: {source})")
            print(f"      内容长度: {len(context.content)} 字符")
            print(f"      Context ID: {context.id}")
    else:
        print("   当前没有代码context")

    # 显示摘要统计
    print("\n📈 Context摘要:")
    summary = await code_rag.get_code_context_summary()

    print(f"   总代码context数: {summary.get('total_code_contexts', 0)}")
    print(f"   来源分布: {summary.get('sources', {})}")
    print(f"   语言分布: {summary.get('languages', {})}")
    print(f"   类型分布: {summary.get('types', {})}")


async def demo_advanced_features(code_rag):
    """演示高级功能"""
    print("\n\n⚡ 演示 5: 高级功能")
    print("=" * 50)

    # 显示索引统计
    print("\n📊 索引统计:")
    stats = code_rag.code_retriever.get_indexer_statistics()
    print(f"   总文件数: {stats['total_files']}")
    print(f"   总代码块数: {stats['total_chunks']}")
    print(f"   语言分布: {stats['files_by_language']}")
    print(f"   代码块类型: {stats['chunks_by_type']}")

    # 搜索特定文件类型
    print("\n📄 按文件类型搜索:")
    file_context_result = await code_rag.add_file_context("src/context/manager.py")
    if file_context_result:
        print(f"   成功添加文件context: {file_context_result}")

    # 批量增强
    print("\n⚡ 批量增强多个查询:")
    batch_queries = ["def __init__", "class Context", "async def search"]

    for query in batch_queries:
        context_ids = await code_rag.enhance_context_with_code(query, max_results=2)
        print(f"   '{query}': 找到 {len(context_ids)} 个结果")


async def demo_performance():
    """演示性能特性"""
    print("\n\n⏱️ 演示 6: 性能测试")
    print("=" * 50)

    import time

    # 测试搜索性能
    context_manager = ContextManager(working_memory_limit=100)
    code_rag = CodeRAGAdapter(
        context_manager=context_manager,
        repo_path=".",
        db_path="temp/rag_data/perf_test_index.db",
    )

    test_queries = ["def", "class", "import", "async", "return"]

    print("\n⏱️ 搜索性能测试:")
    for query in test_queries:
        start_time = time.time()
        context_ids = await code_rag.enhance_context_with_code(query, max_results=5)
        end_time = time.time()

        duration = (end_time - start_time) * 1000  # 转换为毫秒
        print(f"   '{query}': {len(context_ids)} 个结果, 耗时 {duration:.2f}ms")


async def main():
    """主演示函数"""
    print("🚀 代码RAG功能完整演示")
    print("=" * 60)
    print("本演示将展示代码RAG系统的各项功能:")
    print("1. 基本代码搜索")
    print("2. 函数和类搜索")
    print("3. 自动增强功能")
    print("4. Context管理")
    print("5. 高级功能")
    print("6. 性能测试")
    print("=" * 60)

    try:
        # 运行演示
        code_rag, context_manager = await demo_basic_search()
        await demo_function_class_search(code_rag, context_manager)
        await demo_auto_enhancement(code_rag)
        await demo_context_management(code_rag, context_manager)
        await demo_advanced_features(code_rag)
        await demo_performance()

        print("\n\n✅ 所有演示完成!")
        print("代码RAG功能已成功集成到agent系统中。")

        # 清理
        print("\n🧹 清理演示数据...")
        demo_db = Path("temp/rag_data/demo_code_index.db")
        perf_db = Path("temp/rag_data/perf_test_index.db")

        if demo_db.exists():
            demo_db.unlink()
            print("   已删除演示数据库")

        if perf_db.exists():
            perf_db.unlink()
            print("   已删除性能测试数据库")

    except Exception as e:
        print(f"\n❌ 演示过程中出现错误: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    # 运行演示
    asyncio.run(main())
