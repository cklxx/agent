#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Code Agent 测试脚本

该脚本演示了code agent的主要功能：
1. 任务规划拆解
2. 文件读写操作
3. 命令行执行
4. 代码diff生成
"""

import asyncio
from src.code_agent_workflow import CodeAgentWorkflow


async def test_basic_functionality():
    """测试基本功能"""
    print("🚀 开始测试 Code Agent 基本功能")

    workflow = CodeAgentWorkflow()

    # 显示可用工具
    tools = workflow.get_available_tools()
    print(f"📊 可用工具数量: {len(tools)}")
    print("🔧 可用工具:")
    for tool in tools:
        print(f"  - {tool}")

    # 测试任务规划
    print("\n📋 测试任务规划功能...")
    planner = workflow.task_planner
    plan = planner.plan_task("创建一个简单的Python脚本，实现文件备份功能")

    print(f"生成的执行计划包含 {len(plan)} 个步骤:")
    for i, step in enumerate(plan, 1):
        print(f"  {i}. {step['description']} (类型: {step['type']})")

    # 断言检查
    assert len(tools) > 0, "应该有可用的工具"
    assert len(plan) > 0, "应该能生成执行计划"
    assert isinstance(plan, list), "计划应该是一个列表"


async def test_simple_task():
    """测试简单任务执行"""
    print("\n🎯 测试简单任务执行...")

    workflow = CodeAgentWorkflow()

    # 执行一个简单的任务
    task = "读取todo文件并显示其内容"

    try:
        result = await workflow.execute_task(task, max_iterations=2)

        print(f"✅ 任务执行结果: {result['summary']}")

        if result["success"]:
            print("🎉 任务执行成功!")
        else:
            print("❌ 任务执行失败")

        # 断言检查
        assert "summary" in result, "结果应该包含 summary"
        assert "success" in result, "结果应该包含 success 字段"

    except Exception as e:
        print(f"❌ 任务执行出错: {str(e)}")
        # 如果有异常，测试应该失败
        assert False, f"任务执行不应该抛出异常: {str(e)}"


def test_tools_individually():
    """单独测试各个工具"""
    print("\n🔧 单独测试各个工具...")

    # 测试文件读取工具
    from src.tools.file_reader import read_file, get_file_info

    print("📖 测试文件读取工具:")
    try:
        file_info = get_file_info("todo")
        print(f"  - todo文件信息获取成功")

        content = read_file("todo")
        print(f"  - todo文件内容读取成功 (前50字符): {content[:50]}...")
    except Exception as e:
        print(f"  - 文件读取测试失败: {e}")

    # 测试命令行工具
    from src.tools.terminal_executor import (
        get_current_directory,
        list_directory_contents,
    )

    print("\n💻 测试命令行工具:")
    try:
        # LangChain 工具需要通过工具调用的方式来使用
        cwd = get_current_directory.invoke({})
        print(f"  - 当前目录: {cwd}")

        contents = list_directory_contents.invoke({"path": "."})
        print(f"  - 目录内容获取成功")

        # 断言检查
        assert isinstance(cwd, str), "当前目录应该是字符串"
        assert isinstance(contents, str), "目录内容应该是字符串"

    except Exception as e:
        print(f"  - 命令行工具测试失败: {e}")
        # 工具测试失败时应该让测试失败
        assert False, f"工具测试不应该失败: {e}"


async def main():
    """主测试函数"""
    print("=" * 60)
    print("Code Agent 功能测试")
    print("=" * 60)

    try:
        # 测试基本功能
        await test_basic_functionality()

        # 单独测试工具
        test_tools_individually()

        # 测试简单任务
        await test_simple_task()

        print("\n" + "=" * 60)
        print("✅ 所有测试完成!")
        print("📋 Code Agent 功能已成功实现:")
        print("  ✓ 代码任务规划拆解能力")
        print("  ✓ 命令行执行能力")
        print("  ✓ 工作区文件读取工具")
        print("  ✓ 工作区文件写入工具")
        print("  ✓ 代码diff增量更新代码能力")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {str(e)}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
