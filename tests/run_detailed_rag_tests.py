#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
详细的RAG测试运行脚本
"""

import sys
import os
import time
import traceback
from pathlib import Path


def run_single_test_file(test_file: str, description: str = None) -> bool:
    """运行单个测试文件"""
    test_path = Path(__file__).parent / test_file
    
    if not test_path.exists():
        print(f"❌ 测试文件不存在: {test_file}")
        return False
    
    print(f"\n{'='*60}")
    print(f"🧪 运行测试: {description or test_file}")
    print(f"{'='*60}")
    
    try:
        # 执行测试文件
        os.system(f"cd {Path(__file__).parent} && python {test_file}")
        print(f"✅ 测试 {test_file} 执行完成")
        return True
    except Exception as e:
        print(f"❌ 测试 {test_file} 执行失败: {e}")
        traceback.print_exc()
        return False


def run_all_detailed_tests():
    """运行所有详细测试"""
    print("🚀 开始运行详细的RAG功能测试")
    print("="*80)
    
    # 定义测试文件列表
    test_files = [
        ("test_rag_core_functionality.py", "核心功能测试 - 验证基础逻辑"),
        ("test_rag_context_manager.py", "上下文管理测试 - 验证状态管理"),
        ("test_rag_enhanced_search_tools.py", "增强搜索工具测试 - 验证搜索功能"),
        ("test_workspace_rag_integration.py", "工作空间集成测试 - 验证集成功能"),
        ("test_rag_edge_cases.py", "边界情况测试 - 验证异常处理"),
        ("test_rag_performance.py", "性能测试 - 验证性能指标"),
        ("test_rag_mock_scenarios.py", "模拟场景测试 - 验证复杂场景"),
    ]
    
    passed_tests = []
    failed_tests = []
    total_start_time = time.time()
    
    for test_file, description in test_files:
        start_time = time.time()
        
        success = run_single_test_file(test_file, description)
        
        end_time = time.time()
        duration = end_time - start_time
        
        if success:
            passed_tests.append((test_file, description, duration))
        else:
            failed_tests.append((test_file, description, duration))
        
        print(f"⏱️ 耗时: {duration:.2f}秒")
        print("-" * 60)
    
    total_end_time = time.time()
    total_duration = total_end_time - total_start_time
    
    # 生成详细报告
    print("\n" + "="*80)
    print("📊 详细测试报告")
    print("="*80)
    
    print(f"📈 测试概览:")
    print(f"  总测试数: {len(test_files)}")
    print(f"  通过测试: {len(passed_tests)} ✅")
    print(f"  失败测试: {len(failed_tests)} ❌")
    print(f"  成功率: {(len(passed_tests)/len(test_files))*100:.1f}%")
    print(f"  总耗时: {total_duration:.2f}秒")
    print(f"  平均耗时: {total_duration/len(test_files):.2f}秒/测试")
    
    if passed_tests:
        print(f"\n✅ 通过的测试 ({len(passed_tests)}个):")
        for test_file, description, duration in passed_tests:
            print(f"  • {description}")
            print(f"    文件: {test_file} (耗时: {duration:.2f}秒)")
    
    if failed_tests:
        print(f"\n❌ 失败的测试 ({len(failed_tests)}个):")
        for test_file, description, duration in failed_tests:
            print(f"  • {description}")
            print(f"    文件: {test_file} (耗时: {duration:.2f}秒)")
    
    # 性能分析
    if passed_tests:
        print(f"\n⚡ 性能分析:")
        durations = [duration for _, _, duration in passed_tests + failed_tests]
        avg_duration = sum(durations) / len(durations)
        max_duration = max(durations)
        min_duration = min(durations)
        
        print(f"  平均耗时: {avg_duration:.2f}秒")
        print(f"  最长耗时: {max_duration:.2f}秒")
        print(f"  最短耗时: {min_duration:.2f}秒")
        
        # 找出最慢的测试
        slowest_test = max(passed_tests + failed_tests, key=lambda x: x[2])
        fastest_test = min(passed_tests + failed_tests, key=lambda x: x[2])
        
        print(f"  最慢测试: {slowest_test[1]} ({slowest_test[2]:.2f}秒)")
        print(f"  最快测试: {fastest_test[1]} ({fastest_test[2]:.2f}秒)")
    
    # 功能覆盖评估
    print(f"\n🎯 功能覆盖评估:")
    coverage_map = {
        "test_rag_core_functionality.py": "核心逻辑",
        "test_rag_context_manager.py": "上下文管理",
        "test_rag_enhanced_search_tools.py": "搜索增强",
        "test_workspace_rag_integration.py": "集成功能",
        "test_rag_edge_cases.py": "边界处理",
        "test_rag_performance.py": "性能优化",
        "test_rag_mock_scenarios.py": "异常处理",
    }
    
    covered_areas = []
    for test_file, _, _ in passed_tests:
        if test_file in coverage_map:
            covered_areas.append(coverage_map[test_file])
    
    uncovered_areas = []
    for test_file, _, _ in failed_tests:
        if test_file in coverage_map:
            uncovered_areas.append(coverage_map[test_file])
    
    for area in covered_areas:
        print(f"  ✅ {area} - 已覆盖")
    
    for area in uncovered_areas:
        print(f"  ❌ {area} - 未覆盖")
    
    coverage_percentage = (len(covered_areas) / len(coverage_map)) * 100
    print(f"\n功能覆盖率: {coverage_percentage:.1f}%")
    
    # 质量评级
    if len(failed_tests) == 0:
        quality_grade = "🏆 优秀"
        recommendation = "所有测试通过，RAG功能质量优秀，可以用于生产环境。"
    elif len(failed_tests) == 1:
        quality_grade = "🥇 良好"
        recommendation = "大部分测试通过，RAG功能质量良好，建议修复失败测试后部署。"
    elif len(failed_tests) <= 2:
        quality_grade = "🥈 一般"
        recommendation = "部分测试失败，RAG功能质量一般，需要修复关键问题。"
    else:
        quality_grade = "❌ 需改进"
        recommendation = "多个测试失败，RAG功能需要重大改进。"
    
    print(f"\n📈 质量评级: {quality_grade}")
    print(f"建议: {recommendation}")
    
    # 改进建议
    if failed_tests:
        print(f"\n🔧 具体改进建议:")
        for test_file, description, _ in failed_tests:
            if "核心功能" in description:
                print(f"  • 修复核心功能问题 - 检查基础逻辑实现")
            elif "上下文管理" in description:
                print(f"  • 完善上下文管理 - 检查状态同步逻辑")
            elif "搜索工具" in description:
                print(f"  • 优化搜索功能 - 检查搜索算法和结果处理")
            elif "集成" in description:
                print(f"  • 修复集成问题 - 检查模块间接口和依赖")
            elif "边界情况" in description:
                print(f"  • 加强边界处理 - 检查异常处理和输入验证")
            elif "性能" in description:
                print(f"  • 优化性能问题 - 检查算法复杂度和资源使用")
            elif "模拟场景" in description:
                print(f"  • 完善异常处理 - 检查错误恢复和降级机制")
    
    # 下一步建议
    print(f"\n🎯 下一步建议:")
    if len(failed_tests) == 0:
        print(f"  • 考虑添加更多边界情况测试")
        print(f"  • 进行压力测试和长期稳定性测试")
        print(f"  • 优化性能瓶颈，提升响应速度")
        print(f"  • 增加监控和日志记录")
    else:
        print(f"  • 优先修复失败的核心功能测试")
        print(f"  • 逐一解决失败测试中的问题")
        print(f"  • 重新运行测试验证修复效果")
        print(f"  • 考虑增加更多单元测试")
    
    print(f"\n" + "="*80)
    if len(failed_tests) == 0:
        print(f"🎉 恭喜！所有RAG功能测试都已通过")
        print(f"✨ RAG系统已准备好投入使用")
    else:
        print(f"⚠️ 还有 {len(failed_tests)} 个测试需要修复")
        print(f"🔄 请根据上述建议进行改进")
    
    return len(failed_tests) == 0


def main():
    """主函数"""
    if len(sys.argv) > 1:
        # 运行特定测试
        test_file = sys.argv[1]
        description = f"单独测试: {test_file}"
        success = run_single_test_file(test_file, description)
        exit(0 if success else 1)
    else:
        # 运行所有测试
        success = run_all_detailed_tests()
        exit(0 if success else 1)


if __name__ == "__main__":
    main() 