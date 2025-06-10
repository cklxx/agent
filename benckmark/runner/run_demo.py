#!/usr/bin/env python3
"""
AI Agent Benchmark 演示脚本

快速运行一些示例测试，展示测试框架的功能
"""

import asyncio
import json
import sys
from pathlib import Path

# 添加utils目录到路径
sys.path.append(str(Path(__file__).parent / "utils"))

from sandbox_manager import SandboxManager
from evaluator import CodeEvaluator


def print_header(title: str):
    """打印标题"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_section(title: str):
    """打印章节标题"""
    print(f"\n{'-'*40}")
    print(f"  {title}")
    print(f"{'-'*40}")


async def demo_temperature_converter():
    """演示温度转换器任务"""
    print_header("演示: 温度转换器 (入门级)")

    # 任务配置
    task_config = {
        "id": "demo_temp_converter",
        "level": "beginner",
        "domain": "algorithms",
        "title": "温度转换器",
        "evaluation_criteria": {
            "functionality": 40,
            "code_quality": 25,
            "performance": 15,
            "security": 10,
            "documentation": 10,
        },
        "test_cases": [
            {"input": {"value": 0, "unit": "C"}, "expected": (32.0, "F")},
            {"input": {"value": 32, "unit": "F"}, "expected": (0.0, "C")},
            {"input": {"value": -40, "unit": "C"}, "expected": (-40.0, "F")},
            {"input": {"value": 100, "unit": "C"}, "expected": (212.0, "F")},
        ],
        "input_spec": {"function_name": "temperature_converter"},
    }

    # 模拟AI生成的代码（好的实现）
    good_code = '''
def temperature_converter(value, unit):
    """
    温度转换函数
    
    Args:
        value (float): 温度值
        unit (str): 单位 ('C' 表示摄氏度, 'F' 表示华氏度)
    
    Returns:
        tuple: (转换后的温度值, 转换后的单位)
    
    Raises:
        ValueError: 当单位不是 'C' 或 'F' 时
    """
    if unit == 'C':
        # 摄氏度转华氏度: F = C * 9/5 + 32
        fahrenheit = round((value * 9/5) + 32, 1)
        return fahrenheit, 'F'
    elif unit == 'F':
        # 华氏度转摄氏度: C = (F - 32) * 5/9
        celsius = round((value - 32) * 5/9, 1)
        return celsius, 'C'
    else:
        raise ValueError("Invalid unit. Use 'C' for Celsius or 'F' for Fahrenheit.")
'''

    # 模拟AI生成的代码（较差的实现）
    poor_code = """
def temperature_converter(value,unit):
    if unit=='C':
        return (value*9/5)+32,'F'
    if unit=='F':
        return (value-32)*5/9,'C'
"""

    print_section("测试优秀代码实现")
    evaluator = CodeEvaluator()

    result1 = await evaluator.evaluate_code(task_config, good_code)
    print(f"总分: {result1.total_score:.2f}/100")
    print(f"各维度得分:")
    for dim, score in result1.dimension_scores.items():
        print(f"  {dim}: {score:.1f}")

    print_section("测试较差代码实现")
    result2 = await evaluator.evaluate_code(task_config, poor_code)
    print(f"总分: {result2.total_score:.2f}/100")
    print(f"各维度得分:")
    for dim, score in result2.dimension_scores.items():
        print(f"  {dim}: {score:.1f}")

    print_section("详细反馈报告")
    print(evaluator.generate_feedback_report(result1))


async def demo_security_check():
    """演示安全检查功能"""
    print_header("演示: 安全检查功能")

    # 安全的代码
    safe_code = '''
def calculate_sum(numbers):
    """计算数字列表的和"""
    return sum(numbers)
'''

    # 不安全的代码
    unsafe_code = """
import os
import subprocess

def dangerous_function(command):
    # 危险：直接执行系统命令
    os.system(command)
    
    # 危险：使用subprocess
    subprocess.run(command, shell=True)
    
    # 危险：使用eval
    result = eval("2 + 2")
    
    return result
"""

    with SandboxManager() as sandbox:
        print_section("安全代码检查")
        safe_issues = sandbox.check_code_security(safe_code)
        print(f"发现安全问题: {len(safe_issues)}")
        for issue in safe_issues:
            print(f"  - {issue}")

        print_section("不安全代码检查")
        unsafe_issues = sandbox.check_code_security(unsafe_code)
        print(f"发现安全问题: {len(unsafe_issues)}")
        for issue in unsafe_issues:
            print(f"  - {issue}")


async def demo_code_quality_analysis():
    """演示代码质量分析"""
    print_header("演示: 代码质量分析")

    # 高质量代码
    high_quality_code = '''
def fibonacci(n):
    """
    计算斐波那契数列的第n项
    
    Args:
        n (int): 位置索引，从0开始
    
    Returns:
        int: 斐波那契数列的第n项
    
    Raises:
        ValueError: 当n为负数时
    """
    if n < 0:
        raise ValueError("n must be non-negative")
    
    if n <= 1:
        return n
    
    # 使用动态规划避免重复计算
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    
    return b
'''

    # 低质量代码
    low_quality_code = """
def fib(n):
    if n<0:return None
    if n<=1:return n
    return fib(n-1)+fib(n-2)
"""

    with SandboxManager() as sandbox:
        print_section("高质量代码分析")
        quality1 = sandbox.analyze_code_quality(high_quality_code)
        print(f"语法分数: {quality1.get('syntax_score', 0):.1f}")
        print(f"复杂度分数: {quality1.get('complexity_score', 0):.1f}")
        print(f"风格分数: {quality1.get('style_score', 0):.1f}")
        print(f"文档分数: {quality1.get('documentation_score', 0):.1f}")

        if quality1.get("issues"):
            print("发现的问题:")
            for issue in quality1["issues"]:
                print(f"  - {issue}")

        print_section("低质量代码分析")
        quality2 = sandbox.analyze_code_quality(low_quality_code)
        print(f"语法分数: {quality2.get('syntax_score', 0):.1f}")
        print(f"复杂度分数: {quality2.get('complexity_score', 0):.1f}")
        print(f"风格分数: {quality2.get('style_score', 0):.1f}")
        print(f"文档分数: {quality2.get('documentation_score', 0):.1f}")

        if quality2.get("issues"):
            print("发现的问题:")
            for issue in quality2["issues"]:
                print(f"  - {issue}")


async def demo_functional_testing():
    """演示功能测试"""
    print_header("演示: 功能测试")

    # 正确的实现
    correct_code = '''
def binary_search(arr, target):
    """二分搜索算法"""
    left, right = 0, len(arr) - 1
    
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    
    return -1
'''

    # 有错误的实现
    buggy_code = '''
def binary_search(arr, target):
    """二分搜索算法（有bug）"""
    left, right = 0, len(arr)  # Bug: 应该是len(arr) - 1
    
    while left < right:  # Bug: 应该是left <= right
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    
    return -1
'''

    test_cases = [
        {"input": {"arr": [1, 3, 5, 7, 9], "target": 5}, "expected": 2},
        {"input": {"arr": [1, 3, 5, 7, 9], "target": 1}, "expected": 0},
        {"input": {"arr": [1, 3, 5, 7, 9], "target": 9}, "expected": 4},
        {"input": {"arr": [1, 3, 5, 7, 9], "target": 4}, "expected": -1},
        {"input": {"arr": [], "target": 1}, "expected": -1},
    ]

    with SandboxManager() as sandbox:
        print_section("测试正确的实现")
        result1 = sandbox.run_functional_tests(
            correct_code, test_cases, "binary_search"
        )
        print(f"通过测试: {result1['passed']}/{result1['total']}")

        for i, detail in enumerate(result1["details"]):
            status = "✓" if detail["passed"] else "✗"
            print(f"  测试 {i+1}: {status}")

        print_section("测试有错误的实现")
        result2 = sandbox.run_functional_tests(buggy_code, test_cases, "binary_search")
        print(f"通过测试: {result2['passed']}/{result2['total']}")

        for i, detail in enumerate(result2["details"]):
            status = "✓" if detail["passed"] else "✗"
            print(f"  测试 {i+1}: {status}")
            if not detail["passed"] and "error" in detail:
                print(f"    错误: {detail['error']}")


def demo_task_loading():
    """演示任务加载"""
    print_header("演示: 任务配置加载")

    # 检查是否有任务文件
    task_dirs = [Path(__file__).parent / "levels", Path(__file__).parent / "domains"]

    for task_dir in task_dirs:
        if task_dir.exists():
            print_section(f"扫描目录: {task_dir.name}")
            yaml_files = list(task_dir.rglob("*.yaml"))
            print(f"找到 {len(yaml_files)} 个任务文件:")

            for yaml_file in yaml_files[:5]:  # 只显示前5个
                relative_path = yaml_file.relative_to(task_dir)
                print(f"  - {relative_path}")

            if len(yaml_files) > 5:
                print(f"  ... 还有 {len(yaml_files) - 5} 个文件")
        else:
            print(f"目录不存在: {task_dir}")


async def main():
    """主函数"""
    print_header("AI Agent Benchmark 测试框架演示")
    print("本演示展示了测试框架的主要功能:")
    print("1. 代码功能测试")
    print("2. 代码质量分析")
    print("3. 安全性检查")
    print("4. 多维度评估")
    print("5. 任务配置管理")

    try:
        # 演示任务配置加载
        demo_task_loading()

        # 演示代码评估
        await demo_temperature_converter()

        # 演示功能测试
        await demo_functional_testing()

        # 演示安全检查
        await demo_security_check()

        # 演示代码质量分析
        await demo_code_quality_analysis()

        print_header("演示完成")
        print("要运行完整的benchmark测试，请使用:")
        print("  python test_runner.py --level beginner")
        print("  python test_runner.py --domain algorithms")
        print("  python test_runner.py --level all --domain all")

    except Exception as e:
        print(f"\n演示过程中发生错误: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
