#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
优化工具演示 - 展示新工具的性能和功能改进
"""

import asyncio
import time
import os
import sys

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.tools.unified_tools import (
    get_unified_tool_manager,
    get_tool_stats,
    cleanup_unified_tools,
)
from src.tools.middleware import CacheConfig, CachePolicy


async def demo_file_operations():
    """演示文件操作优化"""
    print("=== 文件操作性能演示 ===")

    # 创建工具管理器
    manager = get_unified_tool_manager(
        workspace="/Users/ckl/code/agent",
        cache_config=CacheConfig(policy=CachePolicy.INTELLIGENT, ttl=300, max_size=100),
    )

    # 测试文件读取（第一次调用）
    start_time = time.time()
    result1 = manager.view_file("src/tools/__init__.py", limit=10)
    first_call_time = time.time() - start_time
    print(f"首次读取文件耗时: {first_call_time:.3f}s")

    # 测试文件读取（缓存命中）
    start_time = time.time()
    result2 = manager.view_file("src/tools/__init__.py", limit=10)
    cached_call_time = time.time() - start_time
    print(f"缓存命中耗时: {cached_call_time:.3f}s")
    print(f"性能提升: {(first_call_time / cached_call_time):.1f}x")

    # 验证结果一致性
    print(f"结果一致性: {result1 == result2}")

    return manager


async def demo_async_operations():
    """演示异步操作优化"""
    print("\n=== 异步操作性能演示 ===")

    manager = get_unified_tool_manager(workspace="/Users/ckl/code/agent")

    # 并发文件操作
    files_to_read = [
        "src/tools/__init__.py",
        "src/tools/middleware.py",
        "src/tools/async_tools.py",
        "src/tools/optimized_tools.py",
    ]

    # 串行操作时间
    start_time = time.time()
    for file_path in files_to_read:
        try:
            manager.view_file(file_path, limit=5)
        except Exception as e:
            print(f"读取 {file_path} 失败: {e}")
    serial_time = time.time() - start_time

    # 并行操作时间
    start_time = time.time()
    tasks = []
    for file_path in files_to_read:
        tasks.append(manager.view_file_async(file_path, limit=5))

    try:
        await asyncio.gather(*tasks, return_exceptions=True)
    except Exception as e:
        print(f"并行操作出错: {e}")

    parallel_time = time.time() - start_time

    print(f"串行操作耗时: {serial_time:.3f}s")
    print(f"并行操作耗时: {parallel_time:.3f}s")
    print(f"并行性能提升: {(serial_time / parallel_time):.1f}x")

    return manager


async def demo_error_handling():
    """演示统一错误处理"""
    print("\n=== 错误处理演示 ===")

    manager = get_unified_tool_manager(workspace="/Users/ckl/code/agent")

    # 测试文件不存在错误
    try:
        manager.view_file("nonexistent_file.txt")
    except Exception as e:
        print(f"文件不存在错误: {type(e).__name__}: {e}")

    # 测试权限错误（尝试读取系统文件）
    try:
        manager.view_file("/etc/shadow")
    except Exception as e:
        print(f"权限错误: {type(e).__name__}: {e}")

    # 测试安全错误
    try:
        manager.bash_command("curl http://malicious-site.com")
    except Exception as e:
        print(f"安全错误: {type(e).__name__}: {e}")


async def demo_resource_management():
    """演示资源管理"""
    print("\n=== 资源管理演示 ===")

    manager = get_unified_tool_manager(workspace="/Users/ckl/code/agent")

    # 启动后台进程
    print("启动后台进程...")
    result = manager.bash_command("sleep 10", run_in_background=True)
    print(result)

    # 列出进程
    print("\n当前后台进程:")
    processes = manager.list_processes()
    print(processes)

    # 等待一下
    await asyncio.sleep(2)

    # 再次检查进程状态
    print("\n2秒后进程状态:")
    processes = manager.list_processes()
    print(processes)


def demo_performance_monitoring():
    """演示性能监控"""
    print("\n=== 性能监控演示 ===")

    manager = get_unified_tool_manager(workspace="/Users/ckl/code/agent")

    # 执行一些操作
    manager.list_files("src/tools")
    manager.glob_search("*.py", "src/tools")
    manager.grep_search("import", "src/tools", "*.py")

    # 获取统计信息
    stats = get_tool_stats()
    print("工具使用统计:")
    print(stats)


async def main():
    """主演示函数"""
    print("🚀 优化工具性能演示开始\n")

    try:
        # 文件操作演示
        manager = await demo_file_operations()

        # 异步操作演示
        await demo_async_operations()

        # 错误处理演示
        await demo_error_handling()

        # 资源管理演示
        await demo_resource_management()

        # 性能监控演示
        demo_performance_monitoring()

        print("\n✅ 演示完成")

    except Exception as e:
        print(f"❌ 演示过程中出错: {e}")
        import traceback

        traceback.print_exc()

    finally:
        # 清理资源
        print("\n🧹 清理资源...")
        cleanup_unified_tools()
        print("清理完成")


if __name__ == "__main__":
    asyncio.run(main())
