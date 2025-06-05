# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
Code Agent Workflow for handling coding tasks with planning and execution capabilities.
"""

import asyncio
from typing import List, Dict, Any, Optional
from src.agents.code_agent import create_code_agent, CodeTaskPlanner
from src.tools import (
    execute_terminal_command, get_current_directory, list_directory_contents,
    read_file, read_file_lines, get_file_info,
    write_file, append_to_file, create_new_file, generate_file_diff
)


class CodeAgentWorkflow:
    """代码代理工作流"""
    
    def __init__(self):
        """初始化代码代理工作流"""
        self.task_planner = CodeTaskPlanner()
        
        # 定义可用的工具
        self.code_tools = [
            # 命令行工具
            execute_terminal_command,
            get_current_directory,
            list_directory_contents,
            
            # 文件读取工具
            read_file,
            read_file_lines,
            get_file_info,
            
            # 文件写入工具
            write_file,
            append_to_file,
            create_new_file,
            generate_file_diff,
        ]
        
        # 创建code agent
        self.agent = create_code_agent(self.code_tools)
    
    async def execute_task(self, task_description: str, max_iterations: int = 5) -> Dict[str, Any]:
        """
        执行代码任务
        
        Args:
            task_description: 任务描述
            max_iterations: 最大迭代次数
            
        Returns:
            执行结果字典
        """
        print(f"🚀 开始执行代码任务: {task_description}")
        
        # 1. 任务规划
        print("📋 正在进行任务规划...")
        plan = self.task_planner.plan_task(task_description)
        
        if not plan:
            print("❌ 无法生成任务计划")
            return {"success": False, "error": "无法生成任务计划"}
        
        print(f"📝 生成了 {len(plan)} 个执行步骤:")
        for i, step in enumerate(plan, 1):
            print(f"  {i}. {step['description']} (类型: {step['type']})")
        
        # 2. 逐步执行
        results = []
        for iteration in range(max_iterations):
            print(f"\n🔄 执行轮次 {iteration + 1}/{max_iterations}")
            
            # 获取下一步
            next_step = self.task_planner.get_next_step()
            if not next_step:
                print("✅ 所有步骤已完成")
                break
            
            print(f"🎯 正在执行: {next_step['description']}")
            
            # 构建agent输入
            agent_input = {
                "input": f"任务: {task_description}\n当前步骤: {next_step['description']}\n可用工具: {next_step['tools']}",
                "task_step": next_step,
                "iteration": iteration + 1
            }
            
            try:
                # 执行agent
                result = await self._execute_agent_step(agent_input)
                results.append(result)
                
                # 标记步骤完成
                step_id = self.task_planner.current_step - 1
                self.task_planner.mark_step_completed(step_id, result)
                
                print(f"✅ 步骤完成: {next_step['description']}")
                
            except Exception as e:
                error_msg = f"步骤执行失败: {str(e)}"
                print(f"❌ {error_msg}")
                results.append({"success": False, "error": error_msg})
                break
        
        # 3. 汇总结果
        success_count = sum(1 for r in results if r.get("success", False))
        total_steps = len(results)
        
        final_result = {
            "success": success_count == total_steps and total_steps > 0,
            "task_description": task_description,
            "total_steps": total_steps,
            "completed_steps": success_count,
            "plan": plan,
            "results": results,
            "summary": f"完成了 {success_count}/{total_steps} 个步骤"
        }
        
        print(f"\n📊 任务执行完成: {final_result['summary']}")
        return final_result
    
    async def _execute_agent_step(self, agent_input: Dict[str, Any]) -> Dict[str, Any]:
        """执行单个agent步骤"""
        try:
            # 构建符合LangGraph AgentState的状态
            state = {
                "messages": [
                    {
                        "role": "user", 
                        "content": agent_input["input"]
                    }
                ],
                "locale": "zh-CN",  # 默认中文
                **agent_input
            }
            
            # 调用agent执行
            result = await self.agent.ainvoke(state)
            
            step_info = agent_input.get("task_step", {})
            
            # 解析agent的响应
            if "messages" in result and len(result["messages"]) > 1:
                last_message = result["messages"][-1]
                output = last_message.get("content", "No output")
            else:
                output = "Agent执行完成，但没有返回具体输出"
            
            return {
                "success": True,
                "step_type": step_info.get("type", "unknown"),
                "description": step_info.get("description", ""),
                "tools_used": step_info.get("tools", []),
                "iteration": agent_input.get("iteration", 0),
                "output": output,
                "agent_result": result
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "step_type": agent_input.get("task_step", {}).get("type", "unknown")
            }
    
    def get_available_tools(self) -> List[str]:
        """获取可用工具列表"""
        return [tool.name for tool in self.code_tools]
    
    def get_tool_descriptions(self) -> Dict[str, str]:
        """获取工具描述"""
        descriptions = {}
        for tool in self.code_tools:
            descriptions[tool.name] = tool.description or "无描述"
        return descriptions


async def run_code_agent_workflow(task_description: str, max_iterations: int = 5) -> Dict[str, Any]:
    """
    运行代码代理工作流
    
    Args:
        task_description: 任务描述
        max_iterations: 最大迭代次数
        
    Returns:
        执行结果字典
    """
    workflow = CodeAgentWorkflow()
    return await workflow.execute_task(task_description, max_iterations)


def run_code_agent_sync(task_description: str, max_iterations: int = 5) -> Dict[str, Any]:
    """
    同步运行代码代理工作流
    
    Args:
        task_description: 任务描述
        max_iterations: 最大迭代次数
        
    Returns:
        执行结果字典
    """
    return asyncio.run(run_code_agent_workflow(task_description, max_iterations))


if __name__ == "__main__":
    # 测试代码代理工作流
    test_task = "创建一个简单的Python脚本，实现文件备份功能"
    result = run_code_agent_sync(test_task)
    print(f"\n最终结果: {result}") 