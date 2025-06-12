# SPDX-License-Identifier: MIT

"""
Architect Agent Workflow
智能架构师Agent工作流 - 单节点递归架构实现

本模块实现了基于单个强大架构师节点的工作流系统，该节点具有：
1. 自我递归调用能力
2. 集成所有可用工具
3. 智能任务分解和执行
4. 迭代优化能力
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from src.code.graph.builder import build_graph
from src.config.logging_config import setup_simplified_logging, setup_debug_logging

logger = logging.getLogger(__name__)


class ArchitectAgentWorkflow:
    """
    智能架构师Agent工作流类
    
    特性：
    - 单节点递归架构
    - 集成所有可用工具
    - 智能任务分解
    - 迭代执行优化
    """
    
    def __init__(self, debug: bool = False):
        """
        初始化工作流
        
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
            logger.debug("Architect Agent: Debug logging enabled")
        else:
            setup_simplified_logging()
        
    async def run_async(
        self,
        task: str,
        max_iterations: int = 10,
        locale: str = "zh-CN",
        workspace: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        异步执行架构师Agent任务
        
        Args:
            task: 用户任务描述
            max_iterations: 最大迭代次数
            locale: 语言环境
            context: 额外上下文信息
            **kwargs: 其他配置参数
            
        Returns:
            包含执行结果的字典
        """
        if not task:
            raise ValueError("任务描述不能为空")
            
        logger.info(f"🏗️ 开始执行Architect Agent任务: {task} 工作目录: {workspace}")
        
        # 构建初始状态
        initial_state = {
            "messages": [{"role": "user", "content": task}],
            "locale": locale,
            "iteration_count": 0,
            "max_iterations": max_iterations,
            "execution_completed": False,
            "execution_failed": False,
        }
        
        # 添加上下文信息
        if workspace:
            initial_state["workspace"] = workspace
            
        # 配置参数
        config = {
            "configurable": {
                "thread_id": f"architect_agent_{asyncio.get_event_loop().time()}",
                "max_iterations": max_iterations,
                **kwargs
            },
            "recursion_limit": max_iterations * 2,  # 防止无限递归
        }
        
        try:
            # 执行工作流
            last_state = None
            step_count = 0
            
            async for state in self.graph.astream(
                input=initial_state, 
                config=config, 
                stream_mode="values"
            ):
                step_count += 1
                last_state = state
                
                # 输出中间结果（如果是调试模式）
                if self.debug and isinstance(state, dict):
                    logger.debug(f"Step {step_count}: {list(state.keys())}")
                    
                # 检查是否完成
                if state.get("execution_completed") or state.get("execution_failed"):
                    break
                    
            logger.info("✅ Architect Agent任务执行完成")
            
            # 返回最终结果
            return {
                "success": not last_state.get("execution_failed", False),
                "final_report": last_state.get("final_report", "未生成报告"),
                "iteration_count": last_state.get("iteration_count", 0),
                "step_count": step_count,
                "execution_completed": last_state.get("execution_completed", False),
                "full_state": last_state
            }
            
        except Exception as e:
            logger.error(f"❌ Architect Agent执行失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "final_report": f"执行过程中发生错误: {str(e)}",
                "iteration_count": 0,
                "step_count": 0,
                "execution_completed": False
            }
    
    def run_sync(
        self,
        task: str,
        max_iterations: int = 10,
        locale: str = "zh-CN",
        workspace: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        同步执行架构师Agent任务
        
        Args:
            task: 用户任务描述
            max_iterations: 最大迭代次数
            locale: 语言环境
            context: 额外上下文信息
            **kwargs: 其他配置参数
            
        Returns:
            包含执行结果的字典
        """
        return asyncio.run(self.run_async(
            task=task,
            max_iterations=max_iterations,
            locale=locale,
            workspace=workspace,
            **kwargs
        ))


# 便捷函数
async def run_architect_agent_async(
    task: str,
    debug: bool = False,
    max_iterations: int = 10,
    locale: str = "zh-CN",
    context: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    异步运行Architect Agent的便捷函数
    
    Args:
        task: 用户任务描述
        debug: 是否启用调试模式
        max_iterations: 最大迭代次数
        locale: 语言环境
        context: 额外上下文信息
        **kwargs: 其他配置参数
        
    Returns:
        包含执行结果的字典
    """
    workflow = ArchitectAgentWorkflow(debug=debug)
    return await workflow.run_async(
        task=task,
        max_iterations=max_iterations,
        locale=locale,
        context=context,
        **kwargs
    )


def run_architect_agent(
    task: str,
    debug: bool = False,
    max_iterations: int = 10,
    locale: str = "zh-CN",
    workspace: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    同步运行Architect Agent的便捷函数
    
    Args:
        task: 用户任务描述
        debug: 是否启用调试模式
        max_iterations: 最大迭代次数
        locale: 语言环境
        context: 额外上下文信息
        **kwargs: 其他配置参数
        
    Returns:
        包含执行结果的字典
    """
    workflow = ArchitectAgentWorkflow(debug=debug)
    return workflow.run_sync(
        task=task,
        max_iterations=max_iterations,
        locale=locale,
        workspace=workspace,
        **kwargs
    )


# 主函数用于测试
if __name__ == "__main__":
    import sys
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="Architect Agent 工作流")
    parser.add_argument("task", help="任务描述")
    parser.add_argument("--debug", action="store_true", help="启用调试模式")
    parser.add_argument("--max-iterations", type=int, default=10, help="最大迭代次数")
    parser.add_argument("--locale", default="zh-CN", help="语言环境")
    parser.add_argument("--user-workspace", help="用户原始工作目录")
    
    args = parser.parse_args()
    
    if not args.task:
        print("❌ 错误: 任务描述不能为空")
        sys.exit(1)
    
    print(f"💼 检测到用户工作目录: {args.user_workspace}")
    
    print(f"🏗️ 启动Architect Agent: {args.task}")
    
    result = run_architect_agent(
        task=args.task,
        debug=args.debug,
        max_iterations=args.max_iterations,
        locale=args.locale,
        workspace=args.user_workspace
    )
    
    print("\n" + "="*50)
    print("📋 执行结果:")
    print(f"成功: {result['success']}")
    print(f"迭代次数: {result['iteration_count']}")
    print(f"步骤数: {result['step_count']}")
    print("\n📄 最终报告:")
    print(result['final_report'])
    
    if not result['success']:
        sys.exit(1) 