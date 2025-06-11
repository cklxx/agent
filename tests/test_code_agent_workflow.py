#!/usr/bin/env python3
"""
Code Agent Workflow 测试

测试code agent的完整workflow，包括：
1. 基本功能测试
2. 反思功能测试
3. 重新规划机制测试
4. 错误处理测试
"""

import asyncio
import json
import logging
import os
import sys
import tempfile
from pathlib import Path
from typing import Dict, Any, List

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.code.graph.builder import build_graph_with_memory
from src.config.configuration import Configuration
from src.prompts.planner_model import Plan

# 设置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class CodeAgentWorkflowTester:
    """Code Agent Workflow 测试器"""

    def __init__(self):
        self.graph = build_graph_with_memory()
        self.test_results = []
        self.temp_dir = None

    def setup_test_environment(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp(prefix="code_agent_test_")
        logger.info(f"测试环境创建: {self.temp_dir}")

    def cleanup_test_environment(self):
        """清理测试环境"""
        if self.temp_dir and Path(self.temp_dir).exists():
            import shutil

            shutil.rmtree(self.temp_dir)
            logger.info(f"测试环境清理: {self.temp_dir}")

    async def run_workflow_test(
        self, test_name: str, test_input: Dict[str, Any]
    ) -> Dict[str, Any]:
        """运行单个workflow测试"""
        logger.info(f"\n🧪 开始测试: {test_name}")

        try:
            # 创建测试配置
            config = {
                "configurable": {
                    "thread_id": f"test_{test_name}",
                    "max_search_results": 5,
                    "max_plan_iterations": 3,
                }
            }

            # 运行workflow
            final_state = None
            step_count = 0
            max_steps = 20  # 防止无限循环

            async for event in self.graph.astream(test_input, config):
                step_count += 1
                logger.info(f"步骤 {step_count}: {list(event.keys())}")

                if step_count > max_steps:
                    logger.warning(f"测试 {test_name} 超过最大步数限制")
                    break

                final_state = event

            # 分析结果
            result = self.analyze_test_result(test_name, final_state)
            self.test_results.append(result)

            logger.info(f"✅ 测试 {test_name} 完成")
            return result

        except Exception as e:
            logger.error(f"❌ 测试 {test_name} 失败: {e}")
            result = {
                "test_name": test_name,
                "status": "error",
                "error": str(e),
                "success": False,
            }
            self.test_results.append(result)
            return result

    def analyze_test_result(
        self, test_name: str, final_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """分析测试结果"""
        if not final_state:
            return {
                "test_name": test_name,
                "status": "no_final_state",
                "success": False,
            }

        # 获取最终状态的值
        state_values = None
        for key, value in final_state.items():
            if isinstance(value, dict):
                state_values = value
                break

        if not state_values:
            return {
                "test_name": test_name,
                "status": "no_state_values",
                "success": False,
            }

        # 分析结果
        has_final_report = bool(state_values.get("final_report", "").strip())
        has_plan = state_values.get("current_plan") is not None
        messages = state_values.get("messages", [])
        observations = state_values.get("observations", [])
        plan_iterations = state_values.get("plan_iterations", 0)

        return {
            "test_name": test_name,
            "status": "completed",
            "success": has_final_report,
            "has_final_report": has_final_report,
            "has_plan": has_plan,
            "message_count": len(messages),
            "observation_count": len(observations),
            "plan_iterations": plan_iterations,
            "final_report_length": len(state_values.get("final_report", "")),
            "state_keys": list(state_values.keys()),
        }

    async def test_basic_code_generation(self):
        """测试基本代码生成功能"""
        test_input = {
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "创建一个简单的Python函数，用于计算两个数字的最大公约数(GCD)。包含测试用例和文档。"
                    ),
                }
            ],
            "locale": "zh-CN",
        }

        return await self.run_workflow_test("basic_code_generation", test_input)

    async def test_file_operations(self):
        """测试文件操作功能"""
        test_input = {
            "messages": [
                {
                    "role": "user",
                    "content": (
                        f"在 {self.temp_dir} 目录下创建一个Python模块，包含数据处理工具函数。"
                        "要求：1) 创建utils.py文件 2) 包含数据清洗函数 3) 添加单元测试 4) 创建README文档"
                    ),
                }
            ],
            "locale": "zh-CN",
        }

        return await self.run_workflow_test("file_operations", test_input)

    async def test_debugging_scenario(self):
        """测试调试场景（可能触发反思功能）"""
        test_input = {
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "创建一个有bug的Python脚本，然后调试并修复它。脚本功能：读取CSV文件并进行数据分析。"
                        "要求包含错误的代码、测试、发现错误、修复过程。"
                    ),
                }
            ],
            "locale": "zh-CN",
        }

        return await self.run_workflow_test("debugging_scenario", test_input)

    async def test_complex_project(self):
        """测试复杂项目（可能需要重新规划）"""
        test_input = {
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "创建一个完整的Web API项目，使用FastAPI框架。"
                        "要求：1) 用户管理API 2) 数据库集成 3) 身份验证 4) 单元测试 5) Docker配置 6) API文档"
                    ),
                }
            ],
            "locale": "zh-CN",
        }

        return await self.run_workflow_test("complex_project", test_input)

    async def test_test_failure_scenario(self):
        """测试测试失败场景（应该触发反思重新规划）"""
        test_input = {
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "创建一个Python类用于银行账户管理，但是故意在实现中留下一些逻辑错误，"
                        "然后编写测试用例。测试应该会失败，然后需要修复代码直到所有测试通过。"
                    ),
                }
            ],
            "locale": "zh-CN",
        }

        return await self.run_workflow_test("test_failure_scenario", test_input)

    async def test_incomplete_implementation(self):
        """测试不完整实现场景（应该触发反思）"""
        test_input = {
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "创建一个机器学习模型训练脚本，但是要求非常高的性能和完整的功能。"
                        "如果第一次实现不够完善，应该识别问题并重新规划。"
                    ),
                }
            ],
            "locale": "zh-CN",
        }

        return await self.run_workflow_test("incomplete_implementation", test_input)

    async def run_all_tests(self):
        """运行所有测试"""
        logger.info("🚀 开始Code Agent Workflow测试套件")

        self.setup_test_environment()

        try:
            # 基本功能测试
            await self.test_basic_code_generation()
            await self.test_file_operations()

            # 复杂场景测试
            await self.test_debugging_scenario()
            await self.test_complex_project()

            # 反思功能测试
            await self.test_test_failure_scenario()
            await self.test_incomplete_implementation()

        finally:
            self.cleanup_test_environment()

        # 生成测试报告
        self.generate_test_report()

    def generate_test_report(self):
        """生成测试报告"""
        logger.info("\n📊 测试报告生成")

        total_tests = len(self.test_results)
        successful_tests = sum(1 for r in self.test_results if r.get("success", False))

        print(f"\n{'='*60}")
        print(f"Code Agent Workflow 测试报告")
        print(f"{'='*60}")
        print(f"总测试数: {total_tests}")
        print(f"成功测试: {successful_tests}")
        print(f"失败测试: {total_tests - successful_tests}")
        print(f"成功率: {(successful_tests/total_tests*100):.1f}%")
        print(f"{'='*60}")

        # 详细结果
        for result in self.test_results:
            status_icon = "✅" if result.get("success", False) else "❌"
            print(f"{status_icon} {result['test_name']}")
            print(f"   状态: {result.get('status', 'unknown')}")
            if result.get("success", False):
                print(f"   最终报告长度: {result.get('final_report_length', 0)}字符")
                print(f"   规划迭代次数: {result.get('plan_iterations', 0)}")
                print(f"   观察结果数: {result.get('observation_count', 0)}")
            elif "error" in result:
                print(f"   错误: {result.get('error', 'unknown')}")
            print()

        # 保存详细报告到文件
        report_path = Path("test_code_agent_workflow_report.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(self.test_results, f, ensure_ascii=False, indent=2)

        print(f"详细报告已保存到: {report_path}")


class QuickTester:
    """快速测试器 - 用于简单验证"""

    def __init__(self):
        self.graph = build_graph_with_memory()

    async def quick_test(self, prompt: str):
        """快速测试单个提示"""
        logger.info(f"🚀 快速测试: {prompt[:50]}...")

        test_input = {
            "messages": [{"role": "user", "content": prompt}],
            "locale": "zh-CN",
        }

        config = {
            "configurable": {
                "thread_id": "quick_test",
                "max_search_results": 3,
                "max_plan_iterations": 2,
            }
        }

        step_count = 0
        async for event in self.graph.astream(test_input, config):
            step_count += 1
            logger.info(f"步骤 {step_count}: {list(event.keys())}")

            # 打印最终结果
            for key, value in event.items():
                if isinstance(value, dict) and value.get("final_report"):
                    print(f"\n✅ 最终报告 (长度: {len(value['final_report'])}字符):")
                    print("=" * 50)
                    print(
                        value["final_report"][:500] + "..."
                        if len(value["final_report"]) > 500
                        else value["final_report"]
                    )
                    print("=" * 50)
                    return

            if step_count > 15:  # 防止无限循环
                logger.warning("快速测试超时")
                break


async def main():
    """主函数"""
    if len(sys.argv) > 1 and sys.argv[1] == "quick":
        # 快速测试模式
        tester = QuickTester()
        prompt = (
            " ".join(sys.argv[2:])
            if len(sys.argv) > 2
            else "创建一个简单的Python函数计算斐波那契数列"
        )
        await tester.quick_test(prompt)
    else:
        # 完整测试套件
        tester = CodeAgentWorkflowTester()
        await tester.run_all_tests()


if __name__ == "__main__":
    # 运行示例:
    # python tests/test_code_agent_workflow.py                    # 运行完整测试套件
    # python tests/test_code_agent_workflow.py quick             # 快速测试默认提示
    # python tests/test_code_agent_workflow.py quick "你的测试提示"  # 快速测试自定义提示

    asyncio.run(main())
