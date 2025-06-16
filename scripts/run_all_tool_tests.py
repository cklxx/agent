#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
运行所有工具单元测试的脚本
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def run_tests(test_pattern=None, verbose=False):
    """运行测试"""
    # 测试文件列表
    test_files = [
        "tests/test_workspace_tools.py",
        "tests/test_file_edit_tools.py",
        "tests/test_file_system_tools.py",
        "tests/test_architect_tools.py",
        "tests/test_bash_tool.py",
        "tests/test_maps_tools.py",
        "tests/test_tools.py",  # 原有的工具测试
    ]

    # 如果指定了测试模式，过滤测试文件
    if test_pattern:
        test_files = [f for f in test_files if test_pattern in f]

    print(f"🚀 开始运行工具单元测试...")
    print(f"📁 项目根目录: {project_root}")
    print(f"🧪 测试文件数量: {len(test_files)}")
    print("-" * 60)

    overall_success = True
    results = {}

    for test_file in test_files:
        test_path = project_root / test_file

        if not test_path.exists():
            print(f"⚠️  测试文件不存在: {test_file}")
            results[test_file] = "SKIPPED"
            continue

        print(f"\n📝 运行测试: {test_file}")

        # 构建pytest命令
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            str(test_path),
            "-v" if verbose else "-q",
            "--tb=short",
            "--no-header",
        ]

        try:
            result = subprocess.run(
                cmd,
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=300,  # 5分钟超时
            )

            if result.returncode == 0:
                print(f"✅ 测试通过: {test_file}")
                results[test_file] = "PASSED"
            else:
                print(f"❌ 测试失败: {test_file}")
                if verbose:
                    print("STDOUT:", result.stdout)
                    print("STDERR:", result.stderr)
                results[test_file] = "FAILED"
                overall_success = False

        except subprocess.TimeoutExpired:
            print(f"⏰ 测试超时: {test_file}")
            results[test_file] = "TIMEOUT"
            overall_success = False
        except Exception as e:
            print(f"💥 测试异常: {test_file} - {e}")
            results[test_file] = "ERROR"
            overall_success = False

    # 打印总结
    print("\n" + "=" * 60)
    print("📊 测试结果总结:")
    print("=" * 60)

    for test_file, status in results.items():
        status_icon = {
            "PASSED": "✅",
            "FAILED": "❌",
            "SKIPPED": "⚠️",
            "TIMEOUT": "⏰",
            "ERROR": "💥",
        }.get(status, "❓")

        print(f"{status_icon} {test_file}: {status}")

    # 统计
    passed = sum(1 for s in results.values() if s == "PASSED")
    failed = sum(1 for s in results.values() if s == "FAILED")
    skipped = sum(1 for s in results.values() if s == "SKIPPED")
    errors = sum(1 for s in results.values() if s in ["TIMEOUT", "ERROR"])

    print(f"\n📈 测试统计:")
    print(f"   通过: {passed}")
    print(f"   失败: {failed}")
    print(f"   跳过: {skipped}")
    print(f"   错误: {errors}")
    print(f"   总计: {len(results)}")

    if overall_success:
        print(f"\n🎉 所有测试通过!")
        return 0
    else:
        print(f"\n💔 有测试失败!")
        return 1


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="运行工具单元测试")
    parser.add_argument("--pattern", "-p", help="测试文件名模式过滤", default=None)
    parser.add_argument("--verbose", "-v", help="详细输出", action="store_true")
    parser.add_argument(
        "--quick", "-q", help="快速模式（只运行基本测试）", action="store_true"
    )

    args = parser.parse_args()

    # 快速模式只运行核心测试
    if args.quick:
        args.pattern = "test_tools.py"

    try:
        exit_code = run_tests(args.pattern, args.verbose)
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⛔ 测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 运行测试时发生错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
