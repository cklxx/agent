#!/usr/bin/env python3
# SPDX-License-Identifier: MIT

"""
RAG增强Code Agent命令行工具
"""

import asyncio
import argparse
import logging
import sys
import os
import yaml
from pathlib import Path
from typing import Optional, Dict, Any

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.agents.rag_enhanced_code_agent import create_rag_enhanced_code_agent
from src.tools import (
    execute_terminal_command,
    get_current_directory,
    list_directory_contents,
    read_file,
    read_file_lines,
    get_file_info,
    write_file,
    append_to_file,
    create_new_file,
    generate_file_diff,
)

# 设置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class RAGEnhancedCodeAgentCLI:
    """RAG增强Code Agent命令行界面"""

    def __init__(
        self,
        repo_path: str = ".",
        debug: bool = False,
        config_path: Optional[str] = None,
        working_directory: Optional[str] = None,
    ):
        self.repo_path = repo_path
        self.debug = debug
        self.config_path = config_path
        self.working_directory = working_directory
        self.config = {}

        if debug:
            logging.getLogger().setLevel(logging.DEBUG)

        # 处理工作目录
        if working_directory:
            working_dir = Path(working_directory).resolve()
            if not working_dir.exists():
                print(f"❌ 工作目录不存在: {working_dir}")
                raise FileNotFoundError(f"工作目录不存在: {working_dir}")
            if not working_dir.is_dir():
                print(f"❌ 不是有效目录: {working_dir}")
                raise NotADirectoryError(f"不是有效目录: {working_dir}")

            # 切换到工作目录
            os.chdir(working_dir)
            print(f"🔧 切换到工作目录: {working_dir}")
            self.working_directory = str(working_dir)

        # 加载配置文件
        self._load_config()

        # 初始化工具和代理
        self._setup_tools_and_agent()

    def _load_config(self):
        """加载配置文件"""
        if self.config_path:
            config_file = Path(self.config_path)
            if not config_file.exists():
                print(f"⚠️  指定的配置文件不存在: {config_file}")
                print("🔧 将使用默认配置")
                return
        else:
            # 自动查找配置文件
            possible_configs = ["conf.yml", "conf.yaml", "config.yml", "config.yaml"]
            config_file = None

            for config_name in possible_configs:
                potential_path = Path(config_name)
                if potential_path.exists():
                    config_file = potential_path
                    print(f"🔧 自动找到配置文件: {config_file}")
                    break

            if not config_file:
                print("ℹ️  未找到配置文件，使用默认配置")
                return

        try:
            with open(config_file, "r", encoding="utf-8") as f:
                self.config = yaml.safe_load(f) or {}
            print(f"✅ 配置文件加载成功: {config_file}")

            # 显示配置摘要
            if self.debug and self.config:
                print("🔧 配置摘要:")
                for key, value in self.config.items():
                    if isinstance(value, dict):
                        print(f"   {key}: {len(value)} 项配置")
                    else:
                        print(f"   {key}: {value}")

        except yaml.YAMLError as e:
            print(f"❌ 配置文件格式错误: {e}")
            print("🔧 将使用默认配置")
        except Exception as e:
            print(f"❌ 配置文件加载失败: {e}")
            print("🔧 将使用默认配置")

    def _setup_tools_and_agent(self):
        """设置工具和代理"""
        # 定义可用工具
        self.tools = [
            # 命令行工具
            execute_terminal_command,
            get_current_directory,
            list_directory_contents,
            # 文件读取工具
            read_file,
            read_file_lines,
            get_file_info,
            # 文件写入工具
            write_file,
            append_to_file,
            create_new_file,
            generate_file_diff,
        ]

        # 创建RAG增强的Code Agent
        print(f"🔧 初始化RAG增强Code Agent...")
        print(f"📂 仓库路径: {self.repo_path}")
        if self.working_directory:
            print(f"💼 工作目录: {self.working_directory}")
        if self.config_path:
            print(f"⚙️ 配置文件: {self.config_path}")
        print(f"🛠️ 配置工具: {len(self.tools)} 个")

        try:
            self.agent = create_rag_enhanced_code_agent(
                repo_path=self.working_directory, tools=self.tools
            )
            print("✅ RAG增强Code Agent初始化成功")
        except Exception as e:
            print(f"❌ 初始化失败: {str(e)}")
            raise

    async def execute_task(self, task_description: str) -> dict:
        """执行RAG增强的编程任务"""
        print(f"\n🚀 开始执行RAG增强任务")
        print(f"📋 任务描述: {task_description}")
        print("=" * 80)

        try:
            result = await self.agent.execute_task_with_rag(
                task_description=task_description, max_iterations=5
            )

            # 格式化输出结果
            self._display_results(result)

            return result

        except Exception as e:
            print(f"❌ 任务执行失败: {str(e)}")
            if self.debug:
                import traceback

                traceback.print_exc()
            return {"success": False, "error": str(e)}

    def _display_results(self, result: dict):
        """格式化显示执行结果"""
        print("\n" + "=" * 80)
        print("📊 RAG增强任务执行结果")
        print("=" * 80)

        if result.get("success"):
            print("🎉 任务执行成功！")
        else:
            print("❌ 任务执行失败")
            if result.get("error"):
                print(f"   错误信息: {result['error']}")

        # 显示基本统计信息
        print(f"\n📈 执行统计:")
        print(f"   • 总步骤数: {result.get('total_steps', 0)}")
        print(f"   • 成功步骤: {result.get('successful_steps', 0)}")
        print(f"   • RAG增强: {'是' if result.get('rag_enhanced') else '否'}")
        print(f"   • 上下文使用: {'是' if result.get('context_used') else '否'}")
        print(f"   • 相关文件分析: {result.get('relevant_files_analyzed', 0)} 个")

        # 显示步骤详情
        results = result.get("results", [])
        if results:
            print(f"\n📋 步骤执行详情:")
            for i, step_result in enumerate(results, 1):
                status = "✅" if step_result.get("success") else "❌"
                title = step_result.get("step_title", f"步骤 {i}")
                print(f"   {status} {i}. {title}")

                if not step_result.get("success") and step_result.get("error"):
                    print(f"      错误: {step_result['error']}")

        print("\n" + "=" * 80)

    async def interactive_mode(self):
        """交互模式"""
        print("\n🔮 RAG增强Code Agent 交互模式")
        print("输入 'exit' 或 'quit' 退出")
        print("输入 'help' 查看帮助信息")
        print("-" * 60)

        while True:
            try:
                task = input("\n💬 请描述您的编程任务: ").strip()

                if not task:
                    continue

                if task.lower() in ["exit", "quit", "q"]:
                    print("👋 再见!")
                    break

                if task.lower() == "help":
                    self._show_help()
                    continue

                # 执行任务
                await self.execute_task(task)

            except KeyboardInterrupt:
                print("\n\n👋 用户中断，再见!")
                break
            except Exception as e:
                print(f"❌ 发生错误: {str(e)}")
                if self.debug:
                    import traceback

                    traceback.print_exc()

    def _show_help(self):
        """显示帮助信息"""
        print(
            """
🔮 RAG增强Code Agent 帮助信息

📌 功能特点:
   • RAG增强: 自动检索相关代码模式和实现
   • 上下文感知: 理解项目结构和依赖关系
   • 模式一致: 遵循现有代码风格和架构
   • 智能规划: 基于项目知识进行任务分解

📝 任务示例:
   • "创建一个新的HTTP客户端类，参考现有的API模式"
   • "修改用户认证模块，添加二因子认证功能"
   • "重构数据库连接模块，提高性能和可维护性"
   • "为现有的服务添加缓存层，遵循现有的缓存模式"

🛠️ 可用工具:
   • 文件操作: 读取、写入、创建、修改文件
   • 命令执行: 运行终端命令、测试、构建
   • 代码分析: 差异比较、结构分析

💡 使用技巧:
   • 描述清楚任务需求和期望结果
   • 提及相关的现有代码或模块
   • 指定特定的实现要求或约束条件
        """
        )


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="RAG增强Code Agent命令行工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  %(prog)s --task "创建一个新的用户管理模块"
  %(prog)s --interactive --repo-path ./my-project
  %(prog)s --task "修复登录功能的bug" --debug
  %(prog)s --task "添加缓存功能" --config custom_conf.yml
  %(prog)s --task "重构代码" --working-directory /path/to/project
        """,
    )

    parser.add_argument("--task", "-t", help="要执行的编程任务描述")

    parser.add_argument(
        "--repo-path", "-r", default=".", help="代码仓库路径 (默认: 当前目录)"
    )

    parser.add_argument(
        "--working-directory", "-w", help="工作目录路径 (如果不指定则使用当前目录)"
    )

    parser.add_argument("--config", "-c", help="配置文件路径 (支持 .yml/.yaml 格式)")

    parser.add_argument("--interactive", "-i", action="store_true", help="启动交互模式")

    parser.add_argument("--debug", "-d", action="store_true", help="启用调试模式")

    args = parser.parse_args()

    # 验证仓库路径
    repo_path = Path(args.repo_path).resolve()
    if not repo_path.exists():
        print(f"❌ 仓库路径不存在: {repo_path}")
        sys.exit(1)

    # 创建CLI实例
    try:
        cli = RAGEnhancedCodeAgentCLI(
            repo_path=str(repo_path),
            debug=args.debug,
            config_path=args.config,
            working_directory=args.working_directory,
        )
    except Exception as e:
        print(f"❌ 初始化失败: {str(e)}")
        sys.exit(1)

    # 执行任务
    async def run():
        if args.interactive:
            await cli.interactive_mode()
        elif args.task:
            result = await cli.execute_task(args.task)
            # 根据结果设置退出码
            sys.exit(0 if result.get("success") else 1)
        else:
            parser.print_help()
            print("\n❌ 请指定 --task 或使用 --interactive 模式")
            sys.exit(1)

    # 运行异步主函数
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("\n👋 用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"❌ 程序异常: {str(e)}")
        if args.debug:
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
