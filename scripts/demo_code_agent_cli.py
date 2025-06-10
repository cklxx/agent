#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Code Agent CLI 功能演示脚本

这个脚本演示了Code Agent CLI的各种功能，包括：
1. 代码生成
2. 文件分析
3. 任务自动化
4. 与真实大模型的交互
"""

import asyncio
import os
import sys

# 获取脚本所在目录和项目根目录，但保持当前工作目录不变
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)

# 添加项目根目录到Python路径，以便导入src模块
sys.path.insert(0, project_root)

from code_agent_simple_cli import SimpleCodeAgentCLI


async def demo_code_generation():
    """演示代码生成功能"""
    print("🎯 演示 1: 代码生成功能")
    print("=" * 50)

    cli = SimpleCodeAgentCLI(debug=False)

    task = """创建一个名为calculator.py的Python脚本，实现以下功能：
1. 支持基本的四则运算（加减乘除）
2. 支持命令行参数输入
3. 包含错误处理
4. 添加使用说明和示例
"""

    result = await cli.execute_task(task)

    if result["success"]:
        print("✅ 代码生成成功!")
        # 测试生成的代码
        if os.path.exists("calculator.py"):
            print("📝 生成的文件:")
            with open("calculator.py", "r", encoding="utf-8") as f:
                content = f.read()
                print(content[:500] + "..." if len(content) > 500 else content)
    else:
        print(f"❌ 代码生成失败: {result.get('error')}")

    print("\n" + "=" * 50)


async def demo_file_analysis():
    """演示文件分析功能"""
    print("🎯 演示 2: 文件分析功能")
    print("=" * 50)

    cli = SimpleCodeAgentCLI(debug=False)

    # 分析我们刚创建的list_files.py
    task = """请分析文件 list_files.py 的代码结构、功能和潜在的改进建议：
1. 分析代码的主要功能和实现方式
2. 检查代码质量和最佳实践
3. 提供改进建议
4. 生成详细的分析报告
"""

    result = await cli.execute_task(task)

    if result["success"]:
        print("✅ 文件分析成功!")
    else:
        print(f"❌ 文件分析失败: {result.get('error')}")

    print("\n" + "=" * 50)


async def demo_automation_task():
    """演示任务自动化功能"""
    print("🎯 演示 3: 任务自动化功能")
    print("=" * 50)

    cli = SimpleCodeAgentCLI(debug=False)

    task = """创建一个自动化脚本 project_status.py，具有以下功能：
1. 自动检测当前项目的类型（Python、Node.js等）
2. 统计代码文件数量和行数
3. 检查是否存在配置文件（requirements.txt、package.json等）
4. 生成项目状态报告
5. 支持命令行运行并输出格式化报告
"""

    result = await cli.execute_task(task)

    if result["success"]:
        print("✅ 自动化脚本创建成功!")

        # 测试运行生成的脚本
        if os.path.exists("project_status.py"):
            print("\n🚀 测试运行生成的脚本:")
            import subprocess

            try:
                result = subprocess.run(
                    ["python", "project_status.py"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    print("✅ 脚本运行成功:")
                    print(result.stdout)
                else:
                    print(f"❌ 脚本运行失败: {result.stderr}")
            except subprocess.TimeoutExpired:
                print("⏰ 脚本运行超时")
            except Exception as e:
                print(f"❌ 运行错误: {e}")
    else:
        print(f"❌ 自动化脚本创建失败: {result.get('error')}")

    print("\n" + "=" * 50)


async def demo_interactive_session():
    """演示交互式会话（模拟）"""
    print("🎯 演示 4: 多轮交互功能")
    print("=" * 50)

    cli = SimpleCodeAgentCLI(debug=False)

    # 模拟多轮对话
    tasks = [
        "创建一个utils.py文件，包含常用的工具函数（字符串处理、文件操作、日期时间等）",
        "为utils.py添加单元测试文件test_utils.py",
        "创建一个README.md文档，说明如何使用这些工具函数",
    ]

    for i, task in enumerate(tasks, 1):
        print(f"\n📋 第 {i} 轮任务: {task}")
        print("-" * 30)

        result = await cli.execute_task(task)

        if result["success"]:
            print(f"✅ 第 {i} 轮任务完成!")
        else:
            print(f"❌ 第 {i} 轮任务失败: {result.get('error')}")

    print("\n" + "=" * 50)


def show_generated_files():
    """显示演示过程中生成的文件"""
    print("📁 演示过程中生成的文件:")
    print("=" * 50)

    demo_files = [
        "calculator.py",
        "project_status.py",
        "utils.py",
        "test_utils.py",
        "README.md",
    ]

    for file in demo_files:
        if os.path.exists(file):
            size = os.path.getsize(file)
            print(f"✅ {file} - {size} bytes")
        else:
            print(f"❌ {file} - 未生成")

    print("\n📊 总结:")
    existing_files = [f for f in demo_files if os.path.exists(f)]
    print(f"成功生成: {len(existing_files)}/{len(demo_files)} 个文件")


async def main():
    """主演示函数"""
    print("🤖 Code Agent CLI 功能演示")
    print("=" * 60)
    print("本演示将展示Code Agent CLI的各项核心功能")
    print("包括代码生成、文件分析、任务自动化和多轮交互")
    print("=" * 60)

    try:
        # 演示各个功能
        await demo_code_generation()
        await demo_file_analysis()
        await demo_automation_task()
        await demo_interactive_session()

        # 显示结果
        show_generated_files()

        print("\n🎉 演示完成!")
        print("你可以使用以下命令启动交互式CLI:")
        print("uv run python code_agent_simple_cli.py")

    except KeyboardInterrupt:
        print("\n\n👋 演示被用户中断")
    except Exception as e:
        print(f"\n❌ 演示过程中出现错误: {e}")


def run_main():
    """运行主函数，处理事件循环兼容性"""
    try:
        # 尝试获取当前事件循环
        loop = asyncio.get_running_loop()
        print("⚠️  检测到运行中的事件循环，请在新的终端中运行此脚本")
        return
    except RuntimeError:
        # 没有运行的事件循环，可以安全使用 asyncio.run()
        pass

    # 设置事件循环策略（Windows兼容性）
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(main())


if __name__ == "__main__":
    run_main()
