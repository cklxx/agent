"""
简化版Token统计器使用示例

演示如何使用SimpleTokenTracker进行基本的token统计。
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.simple_token_tracker import (
    SimpleTokenTracker,
    create_tracker,
    get_global_tracker,
)


def example_basic_usage():
    """示例1: 基本使用方法"""
    print("=== 示例1: 基本使用方法 ===")

    # 创建统计器
    tracker = SimpleTokenTracker()

    # 开启session
    tracker.start_session("基本对话测试")

    # 模拟LLM调用并手动添加统计
    print("\n模拟第1次LLM调用...")
    # 假设从response中获取到token信息
    tracker.add_usage(
        input_tokens=100, output_tokens=50, cost=0.0003, model="gpt-4o-mini"
    )

    print("\n模拟第2次LLM调用...")
    tracker.add_usage(
        input_tokens=200, output_tokens=80, cost=0.0006, model="gpt-4o-mini"
    )

    print("\n模拟第3次LLM调用...")
    tracker.add_usage(input_tokens=150, output_tokens=60, cost=0.0045, model="gpt-4o")

    # 查看当前统计
    print("\n当前统计:")
    tracker.print_session_summary()

    # 结束session
    final_report = tracker.end_session()

    return final_report


def example_multiple_sessions():
    """示例2: 多个session管理"""
    print("\n=== 示例2: 多个session管理 ===")

    tracker = SimpleTokenTracker()

    # 第一个session
    tracker.start_session("会话A")
    tracker.add_usage(
        input_tokens=500, output_tokens=200, cost=0.001, model="gpt-4o-mini"
    )
    tracker.add_usage(
        input_tokens=300, output_tokens=150, cost=0.0008, model="gpt-4o-mini"
    )
    tracker.end_session()

    # 第二个session
    tracker.start_session("会话B")
    tracker.add_usage(input_tokens=800, output_tokens=400, cost=0.003, model="gpt-4o")
    tracker.add_usage(input_tokens=600, output_tokens=300, cost=0.0025, model="gpt-4o")
    tracker.end_session()

    # 查看所有sessions
    print(f"\n所有sessions: {tracker.list_sessions()}")

    # 查看特定session报告
    print("\n会话A详情:")
    tracker.print_session_summary("会话A")

    print("\n会话B详情:")
    tracker.print_session_summary("会话B")


def example_global_tracker():
    """示例3: 使用全局统计器"""
    print("\n=== 示例3: 全局统计器 ===")

    # 获取全局统计器
    global_tracker = get_global_tracker()

    global_tracker.start_session("全局会话")
    global_tracker.add_usage(
        input_tokens=1000, output_tokens=500, cost=0.002, model="claude-3.5-sonnet"
    )

    # 在其他地方也可以获取同一个实例
    another_ref = get_global_tracker()
    another_ref.add_usage(
        input_tokens=800, output_tokens=400, cost=0.0015, model="claude-3.5-sonnet"
    )

    global_tracker.print_session_summary()
    global_tracker.end_session()


def example_export_import():
    """示例4: 导出和数据管理"""
    print("\n=== 示例4: 导出和数据管理 ===")

    tracker = SimpleTokenTracker()

    # 创建测试数据
    tracker.start_session("导出测试")
    tracker.add_usage(
        input_tokens=500, output_tokens=250, cost=0.001, model="gpt-4o-mini"
    )
    tracker.add_usage(input_tokens=1000, output_tokens=500, cost=0.003, model="gpt-4o")
    report = tracker.end_session()

    # 导出单个session
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        export_file = f.name

    success = tracker.export_session("导出测试", export_file)
    if success:
        print(f"单个session导出成功: {export_file}")

        # 读取并显示部分内容
        import json

        with open(export_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"导出数据预览: 总费用=${data['session']['total_cost']:.6f}")

        # 清理文件
        os.unlink(export_file)


def example_real_world_usage():
    """示例5: 实际使用场景模拟"""
    print("\n=== 示例5: 实际使用场景模拟 ===")

    # 模拟一个AI助手的对话流程
    tracker = SimpleTokenTracker()

    def simulate_llm_call(prompt: str, model: str = "gpt-4o-mini"):
        """模拟LLM调用"""
        # 这里模拟从实际LLM响应中提取信息
        input_tokens = len(prompt.split()) * 1.3  # 粗略估算
        output_tokens = input_tokens * 0.8  # 模拟输出

        # 模拟不同模型的定价
        if "gpt-4o-mini" in model:
            cost = (input_tokens * 0.15 + output_tokens * 0.6) / 1_000_000
        elif "gpt-4o" in model:
            cost = (input_tokens * 5.0 + output_tokens * 15.0) / 1_000_000
        else:
            cost = 0.001  # 默认费用

        return int(input_tokens), int(output_tokens), cost

    # 开始对话session
    tracker.start_session("AI助手对话-2024-12-15")

    # 模拟多轮对话
    conversations = [
        "你好，请介绍一下人工智能的发展历程",
        "机器学习和深度学习有什么区别？",
        "请详细解释一下Transformer架构的工作原理",
        "如何选择合适的机器学习算法？",
    ]

    for i, prompt in enumerate(conversations, 1):
        print(f"\n第{i}轮对话:")
        print(f"用户: {prompt}")

        # 模拟LLM调用
        input_tokens, output_tokens, cost = simulate_llm_call(prompt)

        # 添加到统计器
        tracker.add_usage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            model="gpt-4o-mini",
        )

    # 查看实时统计
    print("\n实时统计:")
    current_report = tracker.get_current_report()
    print(f"当前费用: ${current_report['total_cost']:.6f}")
    print(f"当前token: {current_report['total_tokens']:,}")

    # 结束对话
    final_report = tracker.end_session()

    # 显示最终统计
    print(f"\n最终统计:")
    print(f"对话轮数: {final_report['total_calls']}")
    print(f"总token: {final_report['total_tokens']:,}")
    print(f"总费用: ${final_report['total_cost']:.6f}")
    print(f"对话时长: {final_report['duration_seconds']:.2f}秒")


def main():
    """运行所有示例"""
    print("🚀 简化版Token统计器示例")
    print("=" * 50)

    try:
        example_basic_usage()
        example_multiple_sessions()
        example_global_tracker()
        example_export_import()
        example_real_world_usage()

        print("\n" + "=" * 50)
        print("✅ 所有示例运行完成！")

    except Exception as e:
        print(f"❌ 运行出错: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
