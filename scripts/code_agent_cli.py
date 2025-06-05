#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Code Agent CLI - 编程助手命令行交互工具

这个CLI工具提供了一个交互式界面来使用Code Agent的强大编程能力。
支持文件操作、代码生成、调试、重构等多种编程任务。
"""

import argparse
import asyncio
import os
import sys
from typing import Optional

# 添加父目录到Python路径，以便导入src模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from InquirerPy import inquirer
from InquirerPy.base.control import Choice

from src.code_agent_workflow import run_code_agent_workflow
from src.agents.code_agent import CodeTaskPlanner


# 预定义的编程任务模板
CODING_TASKS_ZH = [
    "创建一个Python脚本，实现文件备份和恢复功能",
    "分析当前项目的代码结构，生成文档",
    "实现一个简单的Web API服务器",
    "创建数据处理脚本，支持CSV/JSON文件操作",
    "编写单元测试，提高代码覆盖率",
    "重构现有代码，提高代码质量",
    "实现一个命令行工具，支持参数解析",
    "创建配置管理系统",
    "实现日志系统和错误处理",
    "创建数据库连接和ORM操作",
]

CODING_TASKS_EN = [
    "Create a Python script for file backup and recovery",
    "Analyze current project code structure and generate documentation",
    "Implement a simple Web API server",
    "Create data processing script with CSV/JSON support",
    "Write unit tests to improve code coverage",
    "Refactor existing code to improve quality",
    "Implement a command-line tool with argument parsing",
    "Create configuration management system",
    "Implement logging system and error handling",
    "Create database connection and ORM operations",
]


class CodeAgentCLI:
    """Code Agent CLI交互界面"""
    
    def __init__(self, debug: bool = False, max_iterations: int = 8):
        """
        初始化CLI
        
        Args:
            debug: 是否启用调试模式
            max_iterations: 最大执行迭代次数
        """
        self.debug = debug
        self.max_iterations = max_iterations
        self.task_planner = CodeTaskPlanner()
        
    def print_banner(self):
        """显示欢迎横幅"""
        banner = """
╔══════════════════════════════════════════════════════════════╗
║                    🤖 Code Agent CLI                        ║
║                                                              ║
║   智能编程助手 - 使用大模型驱动的代码生成和任务自动化工具      ║
║                                                              ║
║   功能特性:                                                  ║
║   • 🔧 智能代码生成和重构                                     ║
║   • 📁 安全的文件读写操作                                     ║
║   • ⚡ 命令行工具集成                                         ║
║   • 🧠 任务规划和分解                                         ║
║   • 🔍 代码分析和调试                                         ║
║   • 📊 自动化文档生成                                         ║
╚══════════════════════════════════════════════════════════════╝
        """
        print(banner)
    
    def select_language(self) -> str:
        """选择语言"""
        return inquirer.select(
            message="Select language / 选择语言:",
            choices=[
                Choice("zh", "中文"),
                Choice("en", "English"),
            ],
        ).execute()
    
    def show_current_status(self):
        """显示当前工作状态"""
        cwd = os.getcwd()
        files_count = len([f for f in os.listdir(".") if os.path.isfile(f)])
        dirs_count = len([d for d in os.listdir(".") if os.path.isdir(d)])
        
        print(f"\n📍 当前工作目录: {cwd}")
        print(f"📂 目录统计: {dirs_count} 个文件夹, {files_count} 个文件")
        
        # 检查是否是git仓库
        if os.path.exists(".git"):
            try:
                import subprocess
                result = subprocess.run(
                    ["git", "branch", "--show-current"], 
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    branch = result.stdout.strip()
                    print(f"🌿 Git分支: {branch}")
            except:
                pass
    
    def select_task_mode(self, language: str) -> str:
        """选择任务模式"""
        if language == "zh":
            choices = [
                Choice("template", "📋 选择预设编程任务"),
                Choice("custom", "✏️ 自定义编程任务"),
                Choice("file", "📁 分析和处理现有文件"),
                Choice("debug", "🐛 代码调试和修复"),
                Choice("interactive", "💬 交互式编程会话"),
            ]
            message = "请选择任务模式:"
        else:
            choices = [
                Choice("template", "📋 Select predefined coding task"),
                Choice("custom", "✏️ Custom coding task"),
                Choice("file", "📁 Analyze and process existing files"),
                Choice("debug", "🐛 Code debugging and fixing"),
                Choice("interactive", "💬 Interactive coding session"),
            ]
            message = "Please select task mode:"
        
        return inquirer.select(message=message, choices=choices).execute()
    
    def select_template_task(self, language: str) -> str:
        """选择预设任务模板"""
        tasks = CODING_TASKS_ZH if language == "zh" else CODING_TASKS_EN
        custom_option = "[自定义任务]" if language == "zh" else "[Custom Task]"
        
        choices = [Choice("custom", custom_option)] + [
            Choice(i, task) for i, task in enumerate(tasks)
        ]
        
        message = "选择编程任务:" if language == "zh" else "Select coding task:"
        
        selected = inquirer.select(message=message, choices=choices).execute()
        
        if selected == "custom":
            message = "请描述您的编程任务:" if language == "zh" else "Please describe your coding task:"
            return inquirer.text(message=message, multiline=True).execute()
        else:
            return tasks[selected]
    
    def handle_file_analysis(self, language: str) -> str:
        """处理文件分析任务"""
        # 列出当前目录的文件
        files = [f for f in os.listdir(".") if os.path.isfile(f) and not f.startswith(".")]
        
        if not files:
            msg = "当前目录没有可分析的文件" if language == "zh" else "No files found in current directory"
            print(f"❌ {msg}")
            return None
        
        # 选择文件
        message = "选择要分析的文件:" if language == "zh" else "Select file to analyze:"
        file_choices = [Choice(f, f) for f in sorted(files)[:20]]  # 限制显示数量
        
        selected_file = inquirer.select(message=message, choices=file_choices).execute()
        
        # 选择分析类型
        analysis_types = {
            "zh": [
                Choice("structure", "📊 分析代码结构"),
                Choice("optimize", "⚡ 代码优化建议"),
                Choice("document", "📝 生成文档"),
                Choice("test", "🧪 生成测试代码"),
                Choice("refactor", "🔧 重构代码"),
            ],
            "en": [
                Choice("structure", "📊 Analyze code structure"),
                Choice("optimize", "⚡ Code optimization suggestions"),
                Choice("document", "📝 Generate documentation"),
                Choice("test", "🧪 Generate test code"),
                Choice("refactor", "🔧 Refactor code"),
            ]
        }
        
        message = "选择分析类型:" if language == "zh" else "Select analysis type:"
        analysis_type = inquirer.select(
            message=message, 
            choices=analysis_types[language]
        ).execute()
        
        # 构建任务描述
        task_templates = {
            "structure": {
                "zh": f"分析文件 {selected_file} 的代码结构，包括函数、类、模块依赖关系，并生成结构图和说明文档",
                "en": f"Analyze the code structure of file {selected_file}, including functions, classes, module dependencies, and generate structure diagram and documentation"
            },
            "optimize": {
                "zh": f"分析文件 {selected_file} 的代码，提供性能优化建议、代码质量改进建议，并实现优化方案",
                "en": f"Analyze file {selected_file} and provide performance optimization suggestions, code quality improvements, and implement optimization solutions"
            },
            "document": {
                "zh": f"为文件 {selected_file} 生成完整的API文档、使用说明和代码注释",
                "en": f"Generate complete API documentation, usage instructions and code comments for file {selected_file}"
            },
            "test": {
                "zh": f"为文件 {selected_file} 中的代码生成完整的单元测试，包括边界情况和错误处理测试",
                "en": f"Generate comprehensive unit tests for code in file {selected_file}, including edge cases and error handling tests"
            },
            "refactor": {
                "zh": f"重构文件 {selected_file} 的代码，提高可读性、可维护性和性能，遵循最佳实践",
                "en": f"Refactor code in file {selected_file} to improve readability, maintainability and performance, following best practices"
            }
        }
        
        return task_templates[analysis_type][language]
    
    def handle_debug_task(self, language: str) -> str:
        """处理调试任务"""
        message = "请描述您遇到的问题或粘贴错误信息:" if language == "zh" else "Please describe the problem or paste error message:"
        
        problem_description = inquirer.text(
            message=message,
            multiline=True
        ).execute()
        
        # 选择调试类型
        debug_types = {
            "zh": [
                Choice("error", "❌ 修复运行时错误"),
                Choice("logic", "🔍 修复逻辑错误"),
                Choice("performance", "⚡ 性能问题诊断"),
                Choice("code_review", "👀 代码审查"),
            ],
            "en": [
                Choice("error", "❌ Fix runtime errors"),
                Choice("logic", "🔍 Fix logic errors"),
                Choice("performance", "⚡ Performance issue diagnosis"),
                Choice("code_review", "👀 Code review"),
            ]
        }
        
        message = "选择调试类型:" if language == "zh" else "Select debugging type:"
        debug_type = inquirer.select(
            message=message,
            choices=debug_types[language]
        ).execute()
        
        task_templates = {
            "error": {
                "zh": f"请帮我调试和修复以下问题：{problem_description}。请分析错误原因，提供修复方案，并生成修复后的代码。",
                "en": f"Please help debug and fix the following issue: {problem_description}. Analyze the error cause, provide fix solutions, and generate fixed code."
            },
            "logic": {
                "zh": f"请分析以下逻辑问题：{problem_description}。检查代码逻辑，找出问题所在，并提供正确的实现。",
                "en": f"Please analyze the following logic issue: {problem_description}. Check code logic, identify problems, and provide correct implementation."
            },
            "performance": {
                "zh": f"请诊断以下性能问题：{problem_description}。分析性能瓶颈，提供优化方案。",
                "en": f"Please diagnose the following performance issue: {problem_description}. Analyze performance bottlenecks and provide optimization solutions."
            },
            "code_review": {
                "zh": f"请对以下代码进行审查：{problem_description}。检查代码质量、安全性、最佳实践等方面。",
                "en": f"Please review the following code: {problem_description}. Check code quality, security, best practices, etc."
            }
        }
        
        return task_templates[debug_type][language]
    
    async def run_interactive_mode(self, language: str):
        """运行交互式编程会话"""
        session_name = "交互式编程会话" if language == "zh" else "Interactive Coding Session"
        print(f"\n🚀 开始 {session_name}")
        print("=" * 60)
        
        if language == "zh":
            print("💡 提示: 您可以连续提出编程任务，输入 'quit' 或 'exit' 结束会话")
        else:
            print("💡 Tip: You can continuously ask coding tasks, type 'quit' or 'exit' to end session")
        
        task_counter = 1
        
        while True:
            # 获取用户输入
            prompt = f"\n[任务 {task_counter}] 请输入编程任务: " if language == "zh" else f"\n[Task {task_counter}] Enter coding task: "
            
            try:
                task = input(prompt).strip()
                
                if not task:
                    continue
                    
                if task.lower() in ['quit', 'exit', '退出', 'q']:
                    farewell = "再见！感谢使用 Code Agent CLI!" if language == "zh" else "Goodbye! Thank you for using Code Agent CLI!"
                    print(f"\n👋 {farewell}")
                    break
                
                # 执行任务
                print(f"\n🔄 执行任务 {task_counter}: {task}")
                await self.execute_task(task)
                
                task_counter += 1
                
                # 询问是否继续
                continue_msg = "是否继续下一个任务? (y/n): " if language == "zh" else "Continue with next task? (y/n): "
                continue_choice = input(f"\n{continue_msg}").strip().lower()
                
                if continue_choice in ['n', 'no', '不', '否']:
                    break
                    
            except KeyboardInterrupt:
                interrupt_msg = "\n\n用户中断会话" if language == "zh" else "\n\nUser interrupted session"
                print(f"{interrupt_msg}")
                break
            except Exception as e:
                error_msg = f"会话错误: {str(e)}" if language == "zh" else f"Session error: {str(e)}"
                print(f"❌ {error_msg}")
    
    async def execute_task(self, task_description: str):
        """执行编程任务"""
        try:
            print(f"\n🚀 开始执行任务...")
            print("=" * 60)
            
            # 显示任务规划
            print("📋 任务规划阶段...")
            plan = self.task_planner.plan_task(task_description)
            
            if plan:
                print(f"✅ 生成执行计划，包含 {len(plan)} 个步骤:")
                for i, step in enumerate(plan, 1):
                    print(f"  {i}. {step['description']} ({step['type']})")
            
            # 执行任务
            result = await run_code_agent_workflow(
                task_description, 
                max_iterations=self.max_iterations
            )
            
            # 显示结果
            print("\n" + "=" * 60)
            print("📊 执行结果")
            print("=" * 60)
            
            if result['success']:
                print(f"✅ 任务执行成功!")
                print(f"📝 完成步骤: {result['completed_steps']}/{result['total_steps']}")
                print(f"📄 执行摘要: {result['summary']}")
                
                # 显示生成的文件
                if 'results' in result:
                    files_created = []
                    for r in result['results']:
                        if isinstance(r, dict) and 'output' in r:
                            output = r['output']
                            # 简单检测是否提到了文件创建
                            if 'created' in output.lower() or 'generated' in output.lower():
                                files_created.append(output)
                    
                    if files_created:
                        print("\n📁 可能创建的文件:")
                        for file_info in files_created[:3]:  # 只显示前3个
                            print(f"  - {file_info[:100]}...")
            else:
                print(f"❌ 任务执行失败")
                print(f"📝 完成步骤: {result['completed_steps']}/{result['total_steps']}")
                print(f"❌ 错误信息: {result.get('error', '未知错误')}")
            
        except Exception as e:
            print(f"\n❌ 任务执行出现异常: {str(e)}")
            if self.debug:
                import traceback
                traceback.print_exc()
    
    async def run(self):
        """运行CLI主循环"""
        try:
            # 显示欢迎信息
            self.print_banner()
            
            # 显示当前状态
            self.show_current_status()
            
            # 选择语言
            language = self.select_language()
            
            # 选择任务模式
            mode = self.select_task_mode(language)
            
            if mode == "template":
                task = self.select_template_task(language)
            elif mode == "custom":
                message = "请详细描述您的编程任务:" if language == "zh" else "Please describe your coding task in detail:"
                task = inquirer.text(message=message, multiline=True).execute()
            elif mode == "file":
                task = self.handle_file_analysis(language)
            elif mode == "debug":
                task = self.handle_debug_task(language)
            elif mode == "interactive":
                await self.run_interactive_mode(language)
                return
            
            if not task:
                return
            
            # 执行任务
            await self.execute_task(task)
            
        except KeyboardInterrupt:
            print("\n\n👋 用户取消操作，再见!")
        except Exception as e:
            print(f"\n❌ CLI运行错误: {str(e)}")
            if self.debug:
                import traceback
                traceback.print_exc()


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Code Agent CLI - 智能编程助手",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python code_agent_cli.py                    # 启动交互式界面
  python code_agent_cli.py --task "创建API"   # 直接执行任务
  python code_agent_cli.py --debug            # 启用调试模式
  python code_agent_cli.py --max-iterations 10 # 设置最大迭代次数
        """
    )
    
    parser.add_argument(
        "--task", "-t",
        type=str,
        help="直接指定要执行的编程任务"
    )
    
    parser.add_argument(
        "--debug", "-d",
        action="store_true",
        help="启用调试模式，显示详细错误信息"
    )
    
    parser.add_argument(
        "--max-iterations", "-m",
        type=int,
        default=8,
        help="最大执行迭代次数 (默认: 8)"
    )
    
    parser.add_argument(
        "--version", "-v",
        action="version",
        version="Code Agent CLI v1.0.0"
    )
    
    args = parser.parse_args()
    
    # 创建CLI实例
    cli = CodeAgentCLI(debug=args.debug, max_iterations=args.max_iterations)
    
    if args.task:
        # 直接执行指定任务
        await cli.execute_task(args.task)
    else:
        # 运行交互式界面
        await cli.run()


if __name__ == "__main__":
    asyncio.run(main()) 