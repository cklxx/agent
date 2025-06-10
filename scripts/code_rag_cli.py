#!/usr/bin/env python3
"""
代码RAG功能的命令行交互工具

使用方法:
    python scripts/code_rag_cli.py
"""

import asyncio
import argparse
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.context.manager import ContextManager
from src.context.code_rag_adapter import CodeRAGAdapter
from src.context.base import ContextType


class CodeRAGCLI:
    """代码RAG命令行界面"""

    def __init__(self, repo_path: str, db_path: str = "temp/rag_data/code_index.db"):
        self.repo_path = repo_path
        self.db_path = db_path
        self.context_manager = None
        self.code_rag = None

    async def initialize(self):
        """初始化组件"""
        print("正在初始化代码RAG系统...")

        self.context_manager = ContextManager(
            working_memory_limit=100, auto_compress=True
        )

        self.code_rag = CodeRAGAdapter(
            context_manager=self.context_manager,
            repo_path=self.repo_path,
            db_path=self.db_path,
        )

        print("初始化完成!")
        await self.show_statistics()

    async def show_statistics(self):
        """显示统计信息"""
        stats = self.code_rag.code_retriever.get_indexer_statistics()
        print(f"\n📊 索引统计:")
        print(f"   总文件数: {stats['total_files']}")
        print(f"   总代码块数: {stats['total_chunks']}")
        print(f"   语言分布: {stats['files_by_language']}")
        print(f"   代码块类型: {stats['chunks_by_type']}")

    async def search_code(self, query: str):
        """搜索代码"""
        print(f"\n🔍 搜索: '{query}'")

        context_ids = await self.code_rag.enhance_context_with_code(
            query, max_results=5
        )

        if context_ids:
            print(f"   找到 {len(context_ids)} 个相关代码块:")

            for i, context_id in enumerate(context_ids):
                context = await self.context_manager.get_context(context_id)
                if context:
                    file_path = context.metadata.get("file_path", "unknown")
                    language = context.metadata.get("language", "unknown")
                    chunk_count = context.metadata.get("chunk_count", 0)

                    print(
                        f"   {i+1}. {Path(file_path).name} ({language}, {chunk_count} 个代码块)"
                    )
        else:
            print("   未找到相关代码")

    async def search_function(self, function_name: str):
        """搜索函数"""
        print(f"\n🔧 搜索函数: '{function_name}'")

        context_ids = await self.code_rag.search_and_add_function_context(function_name)

        if context_ids:
            print(f"   找到 {len(context_ids)} 个函数定义:")

            for i, context_id in enumerate(context_ids):
                context = await self.context_manager.get_context(context_id)
                if context:
                    file_path = context.metadata.get("file_path", "unknown")
                    print(f"   {i+1}. {function_name}() 在 {Path(file_path).name}")
        else:
            print(f"   未找到函数 '{function_name}'")

    async def search_class(self, class_name: str):
        """搜索类"""
        print(f"\n🏗️ 搜索类: '{class_name}'")

        context_ids = await self.code_rag.search_and_add_class_context(class_name)

        if context_ids:
            print(f"   找到 {len(context_ids)} 个类定义:")

            for i, context_id in enumerate(context_ids):
                context = await self.context_manager.get_context(context_id)
                if context:
                    file_path = context.metadata.get("file_path", "unknown")
                    print(f"   {i+1}. class {class_name} 在 {Path(file_path).name}")
        else:
            print(f"   未找到类 '{class_name}'")

    async def auto_enhance(self, query: str):
        """自动增强"""
        print(f"\n🤖 自动增强: '{query}'")

        result = await self.code_rag.auto_enhance_code_context(query)

        print(f"   增强了 {len(result['enhanced_contexts'])} 个context")
        if result["suggestions"]:
            print("   建议:")
            for suggestion in result["suggestions"]:
                print(f"     - {suggestion}")

    async def list_contexts(self):
        """列出当前context"""
        print("\n📋 当前代码context:")

        contexts = await self.context_manager.search_contexts(
            query="", context_type=ContextType.CODE, limit=20
        )

        if contexts:
            for i, context in enumerate(contexts):
                file_path = context.metadata.get("file_path", "unknown")
                context_type = context.metadata.get("type", "unknown")
                source = context.metadata.get("source", "unknown")

                print(
                    f"   {i+1}. {Path(file_path).name} ({context_type}, 来源: {source})"
                )
        else:
            print("   当前没有代码context")

    async def show_summary(self):
        """显示摘要"""
        print("\n📈 Context摘要:")

        summary = await self.code_rag.get_code_context_summary()

        print(f"   总代码context数: {summary.get('total_code_contexts', 0)}")
        print(f"   来源分布: {summary.get('sources', {})}")
        print(f"   语言分布: {summary.get('languages', {})}")
        print(f"   类型分布: {summary.get('types', {})}")

        recent_queries = summary.get("recent_queries", [])
        if recent_queries:
            print(f"   最近查询: {', '.join(recent_queries[-5:])}")

    def print_help(self):
        """打印帮助信息"""
        print(
            """
🚀 代码RAG命令行工具

可用命令:
  search <query>           - 搜索代码
  function <name>          - 搜索函数
  class <name>             - 搜索类
  auto <query>             - 自动增强查询
  list                     - 列出当前context
  summary                  - 显示摘要统计
  stats                    - 显示索引统计
  help                     - 显示此帮助
  quit/exit                - 退出

示例:
  search ContextManager
  function __init__
  class CodeIndexer
  auto 如何使用ContextManager?
        """
        )

    async def run_interactive(self):
        """运行交互模式"""
        await self.initialize()

        print(
            """
🎯 欢迎使用代码RAG命令行工具!
输入 'help' 查看可用命令，输入 'quit' 或 'exit' 退出。
        """
        )

        while True:
            try:
                command = input("\n> ").strip()

                if not command:
                    continue

                parts = command.split()
                cmd = parts[0].lower()

                if cmd in ["quit", "exit"]:
                    print("再见! 👋")
                    break
                elif cmd == "help":
                    self.print_help()
                elif cmd == "search" and len(parts) > 1:
                    query = " ".join(parts[1:])
                    await self.search_code(query)
                elif cmd == "function" and len(parts) > 1:
                    function_name = parts[1]
                    await self.search_function(function_name)
                elif cmd == "class" and len(parts) > 1:
                    class_name = parts[1]
                    await self.search_class(class_name)
                elif cmd == "auto" and len(parts) > 1:
                    query = " ".join(parts[1:])
                    await self.auto_enhance(query)
                elif cmd == "list":
                    await self.list_contexts()
                elif cmd == "summary":
                    await self.show_summary()
                elif cmd == "stats":
                    await self.show_statistics()
                else:
                    print("   未知命令，输入 'help' 查看可用命令")

            except KeyboardInterrupt:
                print("\n\n操作被中断，输入 'quit' 退出")
            except Exception as e:
                print(f"   错误: {e}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="代码RAG命令行工具")
    parser.add_argument(
        "--repo", "-r", default=".", help="代码仓库路径 (默认: 当前目录)"
    )
    parser.add_argument(
        "--db", "-d", default="temp/rag_data/code_index.db", help="索引数据库路径"
    )

    args = parser.parse_args()

    # 确保仓库路径存在
    repo_path = Path(args.repo).resolve()
    if not repo_path.exists():
        print(f"错误: 仓库路径不存在: {repo_path}")
        sys.exit(1)

    cli = CodeRAGCLI(str(repo_path), args.db)

    # 交互模式
    asyncio.run(cli.run_interactive())


if __name__ == "__main__":
    main()
