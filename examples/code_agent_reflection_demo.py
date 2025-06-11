#!/usr/bin/env python3
"""
Code Agent 反思功能演示

展示code agent的反思和重新规划能力的演示脚本。
包含多个测试场景，特别关注反思功能的触发和工作机制。
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.code.graph.builder import build_graph_with_memory

# 设置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ReflectionDemo:
    """反思功能演示器"""

    def __init__(self):
        self.graph = build_graph_with_memory()

    async def run_demo(self, scenario_name: str, prompt: str, expected_behavior: str):
        """运行演示场景"""
        print(f"\n{'='*80}")
        print(f"🎭 演示场景: {scenario_name}")
        print(f"📝 预期行为: {expected_behavior}")
        print(f"{'='*80}")
        print(f"用户输入: {prompt}")
        print("-" * 80)

        test_input = {
            "messages": [{"role": "user", "content": prompt}],
            "locale": "zh-CN",
        }

        config = {
            "configurable": {
                "thread_id": f"demo_{scenario_name}",
                "max_search_results": 3,
                "max_plan_iterations": 3,
            }
        }

        step_count = 0
        replanning_detected = False
        final_report_generated = False

        try:
            async for event in self.graph.astream(test_input, config):
                step_count += 1

                # 分析当前事件
                for node_name, state in event.items():
                    if isinstance(state, dict):
                        # 检测重新规划
                        messages = state.get("messages", [])
                        if messages:
                            last_message = messages[-1]
                            if (
                                hasattr(last_message, "content")
                                and "质量评估反馈" in last_message.content
                            ):
                                replanning_detected = True
                                print(
                                    f"🔄 步骤 {step_count} [{node_name}]: 检测到反思重新规划!"
                                )
                                print(f"   反馈内容: {last_message.content[:200]}...")
                            elif (
                                hasattr(last_message, "content")
                                and "需要重新规划" in last_message.content
                            ):
                                replanning_detected = True
                                print(
                                    f"🔄 步骤 {step_count} [{node_name}]: 请求重新规划"
                                )

                        # 检测最终报告
                        if state.get("final_report"):
                            final_report_generated = True
                            report_length = len(state["final_report"])
                            plan_iterations = state.get("plan_iterations", 0)
                            print(f"✅ 步骤 {step_count} [{node_name}]: 生成最终报告")
                            print(f"   报告长度: {report_length}字符")
                            print(f"   规划迭代: {plan_iterations}次")
                            print(
                                f"   反思是否触发: {'是' if replanning_detected else '否'}"
                            )

                            # 显示报告摘要
                            report = state["final_report"]
                            if "反思与评估" in report:
                                print(f"   ✨ 包含反思与评估章节")

                            # 显示报告预览
                            print(f"\n📊 最终报告预览:")
                            print("-" * 40)
                            print(report[:300] + "..." if len(report) > 300 else report)
                            print("-" * 40)
                            break
                        else:
                            print(f"⏳ 步骤 {step_count} [{node_name}]: 执行中...")

                if final_report_generated or step_count > 25:  # 防止无限循环
                    break

        except Exception as e:
            print(f"❌ 演示执行出错: {e}")

        # 总结演示结果
        print(f"\n📋 演示总结:")
        print(f"   执行步骤数: {step_count}")
        print(f"   反思功能触发: {'是' if replanning_detected else '否'}")
        print(f"   最终报告生成: {'是' if final_report_generated else '否'}")
        print(f"   演示状态: {'成功' if final_report_generated else '未完成'}")

    async def demo_successful_completion(self):
        """演示成功完成的场景（不触发反思）"""
        await self.run_demo(
            "成功完成场景",
            "创建一个简单的Python函数来计算圆的面积。要求包含函数定义、文档字符串和简单测试。",
            "应该直接成功完成，不触发反思重新规划",
        )

    async def demo_test_failure_reflection(self):
        """演示测试失败触发反思的场景"""
        await self.run_demo(
            "测试失败反思场景",
            "创建一个Python类来模拟简单的计算器，但故意在除法功能中引入零除错误。"
            "然后编写测试用例来验证所有功能，测试应该会失败。"
            "请修复问题并确保所有测试都通过。",
            "应该检测到测试失败，触发反思重新规划",
        )

    async def demo_incomplete_implementation(self):
        """演示不完整实现触发反思的场景"""
        await self.run_demo(
            "不完整实现场景",
            "创建一个完整的用户管理系统，包括用户注册、登录、权限管理、数据持久化、"
            "错误处理、日志记录、单元测试、集成测试、性能测试、安全验证、API文档等。"
            "要求生产级质量。",
            "应该识别实现的不完整性，触发反思重新规划",
        )

    async def demo_quality_issues(self):
        """演示代码质量问题触发反思的场景"""
        await self.run_demo(
            "代码质量问题场景",
            "创建一个文件处理工具，要求能处理大文件、支持多种格式、具备错误恢复能力。"
            "但是第一版实现可能存在性能问题、内存泄露或缺乏错误处理。",
            "应该检测到质量问题，触发反思改进",
        )

    async def demo_dependency_issues(self):
        """演示依赖问题触发反思的场景"""
        await self.run_demo(
            "依赖问题场景",
            "创建一个Web爬虫项目，使用一些特定的Python库。"
            "要求包含完整的依赖管理、环境配置和部署文档。"
            "如果发现依赖配置有问题或缺失，需要重新规划。",
            "应该检测到依赖配置问题，触发反思重新规划",
        )

    async def run_all_demos(self):
        """运行所有演示场景"""
        print(f"🚀 Code Agent 反思功能演示开始")
        print(f"演示目标: 展示agent如何通过反思检测问题并重新规划")

        # 基线场景：正常完成
        await self.demo_successful_completion()

        # 反思触发场景
        await self.demo_test_failure_reflection()
        await self.demo_incomplete_implementation()
        await self.demo_quality_issues()
        await self.demo_dependency_issues()

        print(f"\n🎉 所有演示场景完成!")
        print(f"通过这些演示，您可以看到code agent如何:")
        print(f"1. 在正常情况下直接完成任务")
        print(f"2. 检测测试失败并重新规划")
        print(f"3. 识别实现不完整并改进")
        print(f"4. 发现质量问题并修复")
        print(f"5. 处理依赖配置问题")


async def quick_demo(prompt: str = None):
    """快速演示单个场景"""
    demo = ReflectionDemo()

    if not prompt:
        # 默认演示：故意引入问题来触发反思
        prompt = (
            "创建一个Python脚本来分析CSV数据文件，但是故意在代码中留下一些错误："
            "1) 文件路径硬编码 2) 缺少异常处理 3) 没有输入验证。"
            "然后编写测试用例，测试应该会揭示这些问题。"
            "最后修复所有问题并确保代码质量。"
        )

    await demo.run_demo("快速演示", prompt, "演示反思功能如何检测和修复问题")


async def main():
    """主函数"""
    if len(sys.argv) > 1:
        if sys.argv[1] == "quick":
            # 快速演示模式
            prompt = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else None
            await quick_demo(prompt)
        elif sys.argv[1] == "scenario":
            # 单个场景演示
            demo = ReflectionDemo()
            scenario = sys.argv[2] if len(sys.argv) > 2 else "test_failure"

            if scenario == "success":
                await demo.demo_successful_completion()
            elif scenario == "test_failure":
                await demo.demo_test_failure_reflection()
            elif scenario == "incomplete":
                await demo.demo_incomplete_implementation()
            elif scenario == "quality":
                await demo.demo_quality_issues()
            elif scenario == "dependency":
                await demo.demo_dependency_issues()
            else:
                print(f"未知场景: {scenario}")
                print(
                    "可用场景: success, test_failure, incomplete, quality, dependency"
                )
        else:
            print("未知参数")
            print(
                "用法: python examples/code_agent_reflection_demo.py [quick|scenario] [参数]"
            )
    else:
        # 完整演示
        demo = ReflectionDemo()
        await demo.run_all_demos()


if __name__ == "__main__":
    # 运行示例:
    # python examples/code_agent_reflection_demo.py                              # 完整演示
    # python examples/code_agent_reflection_demo.py quick                        # 快速演示
    # python examples/code_agent_reflection_demo.py quick "自定义测试提示"          # 自定义快速演示
    # python examples/code_agent_reflection_demo.py scenario test_failure        # 单个场景演示

    asyncio.run(main())
