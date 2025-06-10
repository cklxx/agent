#!/usr/bin/env python3
"""
Benchmark 测试清理脚本

清理测试过程中生成的临时文件和无用文件
现在所有临时生成的文件都统一放在 temp_generated/ 目录下
"""

import os
import shutil
import glob
from pathlib import Path
from datetime import datetime


def cleanup_temp_generated():
    """清理 temp_generated 目录下的所有文件"""
    print("🧹 开始清理临时生成的文件...")

    current_dir = Path(__file__).parent
    temp_generated_dir = current_dir / "temp_generated"
    cleanup_count = 0

    if temp_generated_dir.exists():
        print(f"📁 找到临时文件目录: {temp_generated_dir}")

        # 统计要删除的文件和目录数量
        all_items = list(temp_generated_dir.rglob("*"))
        files = [item for item in all_items if item.is_file()]
        dirs = [item for item in all_items if item.is_dir()]

        print(f"📊 临时目录统计: {len(files)} 个文件, {len(dirs)} 个子目录")

        # 删除整个临时目录
        try:
            shutil.rmtree(temp_generated_dir)
            cleanup_count = len(all_items) + 1  # +1 for the main directory
            print(f"🗑️  删除临时目录: temp_generated/")
            print(f"✅ 成功删除 {len(files)} 个文件和 {len(dirs)} 个子目录")
        except Exception as e:
            print(f"❌ 删除临时目录失败: {e}")
    else:
        print("ℹ️  没有找到 temp_generated 目录")

    return cleanup_count


def cleanup_python_cache():
    """清理Python缓存文件"""
    print("\n🧹 清理Python缓存文件...")

    current_dir = Path(__file__).parent
    cleanup_count = 0

    # 清理 __pycache__ 目录
    for pycache_dir in current_dir.rglob("__pycache__"):
        try:
            print(f"🗑️  删除缓存目录: {pycache_dir.relative_to(current_dir)}")
            shutil.rmtree(pycache_dir)
            cleanup_count += 1
        except Exception as e:
            print(f"❌ 删除缓存目录失败: {e}")

    # 清理 .pyc 文件
    for pyc_file in current_dir.rglob("*.pyc"):
        try:
            print(f"🗑️  删除缓存文件: {pyc_file.relative_to(current_dir)}")
            pyc_file.unlink()
            cleanup_count += 1
        except Exception as e:
            print(f"❌ 删除缓存文件失败: {e}")

    print(f"✅ Python缓存清理完成！共删除 {cleanup_count} 个缓存文件/目录")
    return cleanup_count


def cleanup_old_reports():
    """清理旧的测试报告（保留最新的5个）"""
    print("\n🧹 清理旧的测试报告...")

    current_dir = Path(__file__).parent
    reports_dir = current_dir / "reports"
    cleanup_count = 0

    if reports_dir.exists():
        report_files = list(reports_dir.glob("benchmark_report_*.json"))
        if len(report_files) > 5:
            # 按修改时间排序
            report_files.sort(key=lambda x: x.stat().st_mtime)
            old_reports = report_files[:-5]  # 保留最新的5个

            for old_report in old_reports:
                try:
                    print(f"🗑️  删除旧报告: {old_report.name}")
                    old_report.unlink()
                    cleanup_count += 1
                except Exception as e:
                    print(f"❌ 删除报告失败: {e}")

            print(f"✅ 保留最新的 5 个报告，删除了 {cleanup_count} 个旧报告")
        else:
            print(f"ℹ️  现有 {len(report_files)} 个报告，无需清理")
    else:
        print("ℹ️  没有找到 reports 目录")

    return cleanup_count


def cleanup_logs():
    """清理旧的日志文件（保留最新的10个）"""
    print("\n🧹 清理旧的日志文件...")

    current_dir = Path(__file__).parent
    logs_dir = current_dir / "logs"
    cleanup_count = 0

    if logs_dir.exists():
        log_files = list(logs_dir.glob("*.log"))
        if len(log_files) > 10:
            # 按修改时间排序
            log_files.sort(key=lambda x: x.stat().st_mtime)
            old_logs = log_files[:-10]  # 保留最新的10个

            for old_log in old_logs:
                try:
                    print(f"🗑️  删除旧日志: {old_log.name}")
                    old_log.unlink()
                    cleanup_count += 1
                except Exception as e:
                    print(f"❌ 删除日志失败: {e}")

            print(f"✅ 保留最新的 10 个日志，删除了 {cleanup_count} 个旧日志")
        else:
            print(f"ℹ️  现有 {len(log_files)} 个日志文件，无需清理")
    else:
        print("ℹ️  没有找到 logs 目录")

    return cleanup_count


def show_directory_structure():
    """显示清理后的目录结构"""
    print("\n📂 当前目录结构:")
    current_dir = Path(__file__).parent

    important_dirs = [
        ("config", "配置文件"),
        ("levels", "测试级别"),
        ("domains", "测试领域"),
        ("utils", "工具模块"),
        ("reports", "测试报告"),
        ("logs", "日志文件"),
        ("temp_generated", "临时文件"),
    ]

    for dir_name, description in important_dirs:
        dir_path = current_dir / dir_name
        if dir_path.exists():
            if dir_path.is_dir():
                file_count = len(list(dir_path.rglob("*")))
                print(f"  📁 {dir_name}/ - {description} ({file_count} 项)")
            else:
                print(f"  📄 {dir_name} - {description}")
        else:
            print(f"  ❌ {dir_name}/ - {description} (不存在)")


def show_cleanup_summary(temp_count, cache_count, report_count, log_count):
    """显示清理总结"""
    total_count = temp_count + cache_count + report_count + log_count

    print(f"\n📊 清理总结:")
    print(f"  🗑️  临时生成文件: {temp_count} 项")
    print(f"  🗑️  Python缓存: {cache_count} 项")
    print(f"  🗑️  旧测试报告: {report_count} 项")
    print(f"  🗑️  旧日志文件: {log_count} 项")
    print(f"  📈 总计删除: {total_count} 项")


if __name__ == "__main__":
    print("🎯 Benchmark 测试清理工具 v2.0")
    print("=" * 60)
    print(f"⏰ 清理时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🔧 新特性: 统一临时文件管理")
    print("=" * 60)

    # 执行各项清理任务
    temp_count = cleanup_temp_generated()
    cache_count = cleanup_python_cache()
    report_count = cleanup_old_reports()
    log_count = cleanup_logs()

    # 显示结果
    show_directory_structure()
    show_cleanup_summary(temp_count, cache_count, report_count, log_count)

    print("\n🎉 清理完成！Benchmark测试环境已重置为干净状态。")
    print("💡 提示: 所有测试生成的临时文件现在都会统一存放在 temp_generated/ 目录中")
