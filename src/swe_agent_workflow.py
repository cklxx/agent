# SPDX-License-Identifier: MIT

"""
SWE Agent Workflow
软件工程智能Agent工作流 - 专注代码分析、调试和重构

本模块实现了基于SWE(Software Engineering) Agent的工作流系统，专门用于：
1. 代码库深度分析
2. 软件质量评估
3. Bug检测和修复
4. 代码重构建议
5. 技术债务识别
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from langchain_core.messages import HumanMessage
from src.swe.graph.builder import build_graph
from src.config.logging_config import setup_simplified_logging, setup_debug_logging

logger = logging.getLogger(__name__)


class SWEAgentWorkflow:
    """
    软件工程智能Agent工作流类

    特性：
    - 专业代码分析能力
    - 软件质量评估
    - 技术债务识别
    - 自动化重构建议
    - 安全漏洞检测
    """

    def __init__(self, debug: bool = False):
        """
        初始化SWE工作流

        Args:
            debug: 是否启用调试模式
        """
        self.debug = debug
        self.graph = build_graph()
        self._setup_logging()

    def _setup_logging(self):
        """设置日志配置"""
        if self.debug:
            setup_debug_logging()
            logger.debug("SWE Agent: Debug logging enabled")
        else:
            setup_simplified_logging()

    async def run_async(
        self,
        task: str,
        workspace: str,
        max_iterations: int = 10,
        locale: str = "zh-CN",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        异步执行SWE Agent任务

        Args:
            task: 软件工程任务描述
            workspace: 代码库工作目录（必需）
            max_iterations: 最大迭代次数
            locale: 语言环境
            **kwargs: 其他配置参数

        Returns:
            包含执行结果的字典
        """
        if not task:
            raise ValueError("任务描述不能为空")

        if not workspace:
            raise ValueError("工作目录不能为空")

        logger.info(f"🔧 开始执行SWE Agent任务: {task}")
        logger.info(f"📂 工作目录: {workspace}")

        # 构建初始状态
        initial_state = {
            "messages": [HumanMessage(content=task)],
            "workspace": workspace,
            "task_description": task,
            "environment_info": "",
            "recursion_limit": kwargs.get("recursion_limit", 100),
            "iteration_count": 0,
            "max_iterations": max_iterations,
            "execution_completed": False,
            "execution_failed": False,
        }

        # 配置参数
        config = {
            "configurable": {
                "thread_id": f"swe_agent_{asyncio.get_event_loop().time()}",
                "max_iterations": max_iterations,
                **kwargs,
            },
            "recursion_limit": kwargs.get("recursion_limit", 100),
        }

        try:
            # 执行工作流
            last_state = None
            step_count = 0

            async for state in self.graph.astream(
                input=initial_state, config=config, stream_mode="values"
            ):
                step_count += 1
                last_state = state

                # 输出中间结果（如果是调试模式）
                if self.debug and isinstance(state, dict):
                    logger.debug(f"Step {step_count}: {list(state.keys())}")

                # 检查是否完成
                if state.get("execution_completed") or state.get("execution_failed"):
                    break

            logger.info("✅ SWE Agent任务执行完成")

            # 返回最终结果
            return {
                "success": not last_state.get("execution_failed", False),
                "report": last_state.get("report", "未生成报告"),
                "iteration_count": last_state.get("iteration_count", 0),
                "step_count": step_count,
                "execution_completed": last_state.get("execution_completed", False),
                "environment_info": last_state.get("environment_info", ""),
                "workspace": workspace,
                "full_state": last_state,
            }

        except Exception as e:
            logger.error(f"❌ SWE Agent执行失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "report": f"执行过程中发生错误: {str(e)}",
                "iteration_count": 0,
                "step_count": 0,
                "execution_completed": False,
                "workspace": workspace,
            }

    def run_sync(
        self,
        task: str,
        workspace: str,
        max_iterations: int = 10,
        locale: str = "zh-CN",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        同步执行SWE Agent任务

        Args:
            task: 软件工程任务描述
            workspace: 代码库工作目录（必需）
            max_iterations: 最大迭代次数
            locale: 语言环境
            **kwargs: 其他配置参数

        Returns:
            包含执行结果的字典
        """
        return asyncio.run(
            self.run_async(
                task=task,
                workspace=workspace,
                max_iterations=max_iterations,
                locale=locale,
                **kwargs,
            )
        )


# 便捷函数
async def run_swe_agent_async(
    task: str,
    workspace: str,
    debug: bool = False,
    max_iterations: int = 10,
    locale: str = "zh-CN",
    **kwargs,
) -> Dict[str, Any]:
    """
    异步运行SWE Agent的便捷函数

    Args:
        task: 软件工程任务描述
        workspace: 代码库工作目录
        debug: 是否启用调试模式
        max_iterations: 最大迭代次数
        locale: 语言环境
        **kwargs: 其他配置参数

    Returns:
        包含执行结果的字典
    """
    workflow = SWEAgentWorkflow(debug=debug)
    return await workflow.run_async(
        task=task,
        workspace=workspace,
        max_iterations=max_iterations,
        locale=locale,
        **kwargs,
    )


def run_swe_agent(
    task: str,
    workspace: str,
    debug: bool = False,
    max_iterations: int = 10,
    locale: str = "zh-CN",
    **kwargs,
) -> Dict[str, Any]:
    """
    同步运行SWE Agent的便捷函数

    Args:
        task: 软件工程任务描述
        workspace: 代码库工作目录
        debug: 是否启用调试模式
        max_iterations: 最大迭代次数
        locale: 语言环境
        **kwargs: 其他配置参数

    Returns:
        包含执行结果的字典
    """
    workflow = SWEAgentWorkflow(debug=debug)
    return workflow.run_sync(
        task=task,
        workspace=workspace,
        max_iterations=max_iterations,
        locale=locale,
        **kwargs,
    )


# 预定义的SWE任务模板
SWE_TASK_TEMPLATES = {
    "code_analysis": "分析整个代码库，识别潜在的改进区域，并创建简要报告",
    "todo_finder": "查找源代码中所有包含'TODO'或'FIXME'注释的位置并列出它们的位置",
    "dependency_check": "基于pyproject.toml，验证所有依赖项是否正确导入和使用",
    "structure_summary": "生成项目结构摘要，突出显示关键模块及其用途",
    "security_scan": "扫描代码库以识别潜在的安全漏洞和风险",
    "performance_analysis": "分析代码性能瓶颈并提供优化建议",
    "test_coverage": "分析测试覆盖率并识别测试不足的区域",
    "refactor_suggestions": "识别需要重构的代码区域并提供建议",
}


def get_swe_task_template(task_key: str) -> str:
    """
    获取预定义的SWE任务模板

    Args:
        task_key: 任务键值

    Returns:
        任务描述字符串
    """
    return SWE_TASK_TEMPLATES.get(task_key, task_key)


# 主函数用于测试
if __name__ == "__main__":
    import sys
    import argparse
    import os

    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description="SWE Agent 工作流 - 软件工程智能助手",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python src/swe_agent_workflow.py --task "分析代码质量" --workspace /path/to/project
  python src/swe_agent_workflow.py --preset code_analysis --workspace .
  python src/swe_agent_workflow.py --preset todo_finder --workspace . --debug
        """,
    )

    parser.add_argument("--task", help="任务描述")
    parser.add_argument(
        "--preset", choices=list(SWE_TASK_TEMPLATES.keys()), help="使用预定义任务模板"
    )
    parser.add_argument("--workspace", help="代码库工作目录", default=".")
    parser.add_argument("--debug", action="store_true", help="启用调试模式")
    parser.add_argument("--max-iterations", type=int, default=10, help="最大迭代次数")
    parser.add_argument("--locale", default="zh-CN", help="语言环境")
    parser.add_argument("--recursion-limit", type=int, default=100, help="递归限制")

    args = parser.parse_args()

    # 确定任务
    if args.preset:
        task = get_swe_task_template(args.preset)
        print(f"📋 使用预设任务: {args.preset}")
    elif args.task:
        task = args.task
    else:
        print("❌ 错误: 必须指定 --task 或 --preset")
        parser.print_help()
        sys.exit(1)

    # 验证工作目录
    workspace = os.path.abspath(args.workspace)
    if not os.path.exists(workspace):
        print(f"❌ 错误: 工作目录不存在: {workspace}")
        sys.exit(1)

    print(f"🔧 启动SWE Agent: {task}")
    print(f"📂 工作目录: {workspace}")

    try:
        result = run_swe_agent(
            task=task,
            workspace=workspace,
            debug=args.debug,
            max_iterations=args.max_iterations,
            locale=args.locale,
            recursion_limit=args.recursion_limit,
        )

        print("\n" + "=" * 60)
        print("📋 SWE Agent执行结果:")
        print(f"✅ 成功: {result['success']}")
        print(f"🔄 迭代次数: {result['iteration_count']}")
        print(f"📊 步骤数: {result['step_count']}")

        if result.get("environment_info"):
            print(f"🌍 环境信息: {result['environment_info'][:100]}...")

        print("\n📄 最终报告:")
        print("-" * 40)
        print(result["report"])
        print("-" * 40)

        if not result["success"]:
            print(f"❌ 错误: {result.get('error', '未知错误')}")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n⏸️ 用户中断执行")
        sys.exit(0)
    except Exception as e:
        print(f"❌ 执行失败: {e}")
        sys.exit(1)
