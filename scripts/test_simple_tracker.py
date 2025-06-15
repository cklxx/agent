#!/usr/bin/env python3
"""
简化版Token统计器测试脚本

快速验证SimpleTokenTracker的核心功能。
"""

import sys
import os
import tempfile
import json

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils import SimpleTokenTracker, create_tracker, get_global_tracker


def test_basic_functionality():
    """测试基本功能"""
    print("🧪 测试基本功能...")

    tracker = SimpleTokenTracker()

    # 测试session管理
    tracker.start_session("测试session")
    assert tracker.current_session == "测试session"

    # 测试添加使用记录
    tracker.add_usage(
        input_tokens=100, output_tokens=50, cost=0.001, model="test-model"
    )

    # 测试获取报告
    report = tracker.get_current_report()
    assert report["total_calls"] == 1
    assert report["total_input_tokens"] == 100
    assert report["total_output_tokens"] == 50
    assert report["total_tokens"] == 150
    assert abs(report["total_cost"] - 0.001) < 0.000001

    # 测试结束session
    final_report = tracker.end_session()
    assert tracker.current_session is None
    assert final_report["total_calls"] == 1

    print("✅ 基本功能测试通过")
    return True


def test_multiple_usage():
    """测试多次使用记录"""
    print("🧪 测试多次使用记录...")

    tracker = SimpleTokenTracker()
    tracker.start_session("多次使用测试")

    # 添加多次记录
    tracker.add_usage(100, 50, 0.001, "model1")
    tracker.add_usage(200, 80, 0.002, "model2")
    tracker.add_usage(150, 60, 0.0015, "model1")

    report = tracker.get_current_report()

    # 验证总计
    assert report["total_calls"] == 3
    assert report["total_input_tokens"] == 450
    assert report["total_output_tokens"] == 190
    assert report["total_tokens"] == 640
    assert abs(report["total_cost"] - 0.0045) < 0.000001

    # 验证模型分类
    assert len(report["model_breakdown"]) == 2
    assert report["model_breakdown"]["model1"]["calls"] == 2
    assert report["model_breakdown"]["model2"]["calls"] == 1

    tracker.end_session()
    print("✅ 多次使用记录测试通过")
    return True


def test_session_management():
    """测试session管理"""
    print("🧪 测试session管理...")

    tracker = SimpleTokenTracker()

    # 创建多个sessions
    tracker.start_session("session1")
    tracker.add_usage(100, 50, 0.001, "model1")
    tracker.end_session()

    tracker.start_session("session2")
    tracker.add_usage(200, 80, 0.002, "model2")
    tracker.end_session()

    # 验证sessions列表
    sessions = tracker.list_sessions()
    assert "session1" in sessions
    assert "session2" in sessions
    assert len(sessions) == 2

    # 验证获取特定session报告
    report1 = tracker.get_session_report("session1")
    assert report1["total_calls"] == 1
    assert report1["total_cost"] == 0.001

    report2 = tracker.get_session_report("session2")
    assert report2["total_calls"] == 1
    assert report2["total_cost"] == 0.002

    print("✅ session管理测试通过")
    return True


def test_export_functionality():
    """测试导出功能"""
    print("🧪 测试导出功能...")

    tracker = SimpleTokenTracker()
    tracker.start_session("导出测试")
    tracker.add_usage(500, 200, 0.003, "test-model")
    tracker.end_session()

    # 测试导出单个session
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        temp_file = f.name

    try:
        success = tracker.export_session("导出测试", temp_file)
        assert success

        # 验证导出文件
        with open(temp_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "export_time" in data
        assert "session" in data
        assert data["session"]["total_calls"] == 1
        assert data["session"]["total_cost"] == 0.003

    finally:
        os.unlink(temp_file)

    print("✅ 导出功能测试通过")
    return True


def test_global_tracker():
    """测试全局统计器"""
    print("🧪 测试全局统计器...")

    # 获取全局统计器
    global_tracker1 = get_global_tracker()
    global_tracker2 = get_global_tracker()

    # 验证是同一个实例
    assert global_tracker1 is global_tracker2

    # 测试全局统计器功能
    global_tracker1.start_session("全局测试")
    global_tracker1.add_usage(300, 100, 0.0015, "global-model")

    # 从另一个引用添加
    global_tracker2.add_usage(400, 150, 0.002, "global-model")

    report = global_tracker1.get_current_report()
    assert report["total_calls"] == 2
    assert report["total_cost"] == 0.0035

    global_tracker1.end_session()
    print("✅ 全局统计器测试通过")
    return True


def test_error_handling():
    """测试错误处理"""
    print("🧪 测试错误处理...")

    tracker = SimpleTokenTracker()

    # 测试没有session时添加使用记录
    try:
        tracker.add_usage(100, 50, 0.001, "model")
        assert False, "应该抛出ValueError"
    except ValueError:
        pass  # 预期的错误

    # 测试获取不存在的session
    report = tracker.get_session_report("不存在的session")
    assert report is None

    print("✅ 错误处理测试通过")
    return True


def main():
    """运行所有测试"""
    print("🚀 开始简化版Token统计器测试")
    print("=" * 50)

    tests = [
        test_basic_functionality,
        test_multiple_usage,
        test_session_management,
        test_export_functionality,
        test_global_tracker,
        test_error_handling,
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
                print(f"❌ {test_func.__name__} 失败")
        except Exception as e:
            failed += 1
            print(f"❌ {test_func.__name__} 异常: {e}")

    print("\n" + "=" * 50)
    print(f"🎯 测试结果: {passed}个通过, {failed}个失败")

    if failed == 0:
        print("🎉 所有测试通过！简化版Token统计器工作正常。")
        return 0
    else:
        print("⚠️  部分测试失败，请检查代码。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
