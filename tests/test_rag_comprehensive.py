#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
RAG功能综合测试套件
"""

import sys
import time
from pathlib import Path


def run_comprehensive_rag_tests():
    """运行所有RAG相关的测试"""
    print("🚀 开始RAG功能综合测试")
    print("="*80)
    
    test_modules = [
        ("边界情况测试", "test_rag_edge_cases"),
        ("性能测试", "test_rag_performance"),
        ("模拟场景测试", "test_rag_mock_scenarios"),
        ("核心功能测试", "test_rag_core_functionality"),
        ("上下文管理测试", "test_rag_context_manager"),
        ("增强搜索工具测试", "test_rag_enhanced_search_tools"),
        ("工作空间集成测试", "test_workspace_rag_integration"),
    ]
    
    total_passed = 0
    total_failed = 0
    results = []
    
    start_time = time.time()
    
    for test_name, test_module in test_modules:
        print(f"\n🧪 运行 {test_name}...")
        print("-" * 60)
        
        try:
            # 动态导入测试模块
            module = __import__(test_module, fromlist=[''])
            
            # 查找并运行测试函数
            if hasattr(module, 'run_edge_case_tests'):
                success = module.run_edge_case_tests()
            elif hasattr(module, 'run_performance_tests'):
                success = module.run_performance_tests()
            elif hasattr(module, 'run_mock_scenario_tests'):
                success = module.run_mock_scenario_tests()
            elif hasattr(module, 'run_core_functionality_tests'):
                success = module.run_core_functionality_tests()
            elif hasattr(module, 'run_rag_context_tests'):
                success = module.run_rag_context_tests()
            elif hasattr(module, 'run_rag_enhanced_search_tests'):
                success = module.run_rag_enhanced_search_tests()
            elif hasattr(module, 'run_workspace_integration_tests'):
                success = module.run_workspace_integration_tests()
            else:
                print(f"⚠️ 未找到测试运行函数在模块 {test_module}")
                success = False
            
            if success:
                total_passed += 1
                status = "✅ 通过"
            else:
                total_failed += 1
                status = "❌ 失败"
            
            results.append((test_name, status))
            
        except ImportError as e:
            print(f"⚠️ 无法导入测试模块 {test_module}: {e}")
            total_failed += 1
            results.append((test_name, "❌ 导入失败"))
        except Exception as e:
            print(f"❌ 测试执行出错 {test_name}: {e}")
            total_failed += 1
            results.append((test_name, "❌ 执行出错"))
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # 汇总报告
    print("\n" + "="*80)
    print("📊 RAG功能综合测试汇总报告")
    print("="*80)
    
    print(f"测试总数: {len(test_modules)}")
    print(f"通过测试: {total_passed} ✅")
    print(f"失败测试: {total_failed} ❌")
    print(f"成功率: {(total_passed/len(test_modules))*100:.1f}%")
    print(f"总耗时: {total_time:.2f}秒")
    
    print(f"\n📋 详细结果:")
    for test_name, status in results:
        print(f"  {status} {test_name}")
    
    # 功能覆盖评估
    print(f"\n🎯 功能覆盖评估:")
    coverage_areas = [
        ("工作空间安全", "边界情况测试" in [r[0] for r in results if "✅" in r[1]]),
        ("性能优化", "性能测试" in [r[0] for r in results if "✅" in r[1]]),
        ("异常处理", "模拟场景测试" in [r[0] for r in results if "✅" in r[1]]),
        ("核心逻辑", "核心功能测试" in [r[0] for r in results if "✅" in r[1]]),
        ("上下文管理", "上下文管理测试" in [r[0] for r in results if "✅" in r[1]]),
        ("搜索增强", "增强搜索工具测试" in [r[0] for r in results if "✅" in r[1]]),
        ("集成功能", "工作空间集成测试" in [r[0] for r in results if "✅" in r[1]]),
    ]
    
    covered_areas = sum(1 for _, covered in coverage_areas if covered)
    coverage_percentage = (covered_areas / len(coverage_areas)) * 100
    
    for area_name, covered in coverage_areas:
        status = "✅" if covered else "❌"
        print(f"  {status} {area_name}")
    
    print(f"\n功能覆盖率: {coverage_percentage:.1f}% ({covered_areas}/{len(coverage_areas)})")
    
    # 质量评级
    if total_failed == 0 and coverage_percentage == 100:
        grade = "🏆 优秀 (A+)"
        message = "所有测试通过，功能完整，质量卓越！"
    elif total_failed <= 1 and coverage_percentage >= 85:
        grade = "🥇 良好 (A)"
        message = "大部分测试通过，功能基本完整，质量良好。"
    elif total_failed <= 2 and coverage_percentage >= 70:
        grade = "🥈 一般 (B)"
        message = "多数测试通过，功能部分完整，质量一般。"
    elif total_failed <= 3 and coverage_percentage >= 50:
        grade = "🥉 需改进 (C)"
        message = "部分测试通过，功能覆盖不足，需要改进。"
    else:
        grade = "❌ 不合格 (D)"
        message = "多数测试失败，功能不完整，需要重大修复。"
    
    print(f"\n📈 质量评级: {grade}")
    print(f"评语: {message}")
    
    # 改进建议
    if total_failed > 0:
        print(f"\n🔧 改进建议:")
        failed_tests = [r[0] for r in results if "❌" in r[1]]
        for failed_test in failed_tests:
            if "边界情况" in failed_test:
                print(f"  • 加强边界情况处理，检查路径验证和异常处理逻辑")
            elif "性能" in failed_test:
                print(f"  • 优化性能瓶颈，检查算法复杂度和内存使用")
            elif "模拟场景" in failed_test:
                print(f"  • 完善错误处理机制，增强系统健壮性")
            elif "核心功能" in failed_test:
                print(f"  • 修复核心逻辑错误，确保基础功能正常")
            elif "上下文" in failed_test:
                print(f"  • 完善上下文管理，确保状态同步正确")
            elif "搜索" in failed_test:
                print(f"  • 优化搜索算法，提高结果准确性")
            elif "集成" in failed_test:
                print(f"  • 修复集成问题，确保模块间协调工作")
    
    # 最终结论
    if total_failed == 0:
        print(f"\n🎉 恭喜！RAG功能已通过所有综合测试")
        print(f"✨ 系统已准备好在生产环境中使用")
    else:
        print(f"\n⚠️ RAG功能需要进一步改进")
        print(f"🔄 请修复失败的测试后重新运行综合测试")
    
    return total_failed == 0


if __name__ == "__main__":
    # 将当前目录添加到Python路径，以便导入其他测试模块
    current_dir = Path(__file__).parent
    sys.path.insert(0, str(current_dir))
    
    success = run_comprehensive_rag_tests()
    exit(0 if success else 1) 