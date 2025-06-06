# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
Code Agent Workflow for handling coding tasks with planning and execution capabilities.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from src.agents.code_agent import create_code_agent, CodeTaskPlanner
from src.tools import (
    execute_terminal_command, get_current_directory, list_directory_contents,
    read_file, read_file_lines, get_file_info,
    write_file, append_to_file, create_new_file, generate_file_diff
)

# 设置日志
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 如果没有handler，添加一个console handler
if not logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('🚀 [Workflow] %(asctime)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

# 设置LLM Agent日志
llm_agent_logger = logging.getLogger("code_agent_llm_execution")
llm_agent_logger.setLevel(logging.INFO)

# 如果没有handler，添加一个console handler
if not llm_agent_logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('🧠 [LLM] %(asctime)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S')
    console_handler.setFormatter(formatter)
    llm_agent_logger.addHandler(console_handler)


class CodeAgentWorkflow:
    """代码代理工作流"""
    
    def __init__(self):
        """初始化代码代理工作流"""
        logger.info("初始化代码代理工作流")
        
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
        
        logger.info(f"配置 {len(self.code_tools)} 个工具")
        
        # 创建code agent
        try:
            self.agent = create_code_agent(self.code_tools)
            logger.info("代码代理创建成功")
        except Exception as e:
            logger.error(f"创建代码代理失败: {str(e)}")
            raise
    
    async def execute_task(self, task_description: str, max_iterations: int = 5) -> Dict[str, Any]:
        """
        执行代码任务
        
        Args:
            task_description: 任务描述
            max_iterations: 最大迭代次数
            
        Returns:
            执行结果字典
        """
        logger.info(f"开始执行代码任务: {task_description[:100]}{'...' if len(task_description) > 100 else ''}")
        
        # 1. 任务规划
        logger.info("开始任务规划")
        plan = self.task_planner.plan_task(task_description)
        
        if not plan:
            logger.error("任务规划失败")
            return {"success": False, "error": "无法生成任务计划"}
        
        logger.info(f"任务规划完成，生成 {len(plan)} 个执行步骤")
        for i, step in enumerate(plan, 1):
            logger.debug(f"步骤 {i}: {step['description']} (类型: {step['type']})")
        
        # 2. 逐步执行
        results = []
        for iteration in range(max_iterations):
            logger.info(f"开始执行轮次 {iteration + 1}/{max_iterations}")
            
            # 获取下一步
            next_step = self.task_planner.get_next_step()
            if not next_step:
                logger.info("所有步骤已完成")
                break
            
            logger.info(f"执行步骤: {next_step['description']}")
            
            # 构建agent输入
            agent_input = {
                "input": f"任务: {task_description}\n当前步骤: {next_step['description']}\n可用工具: {next_step['tools']}",
                "task_step": next_step,
                "iteration": iteration + 1
            }
            
            try:
                # 执行agent
                logger.debug("调用Agent执行步骤")
                result = await self._execute_agent_step(agent_input)
                results.append(result)
                
                # 标记步骤完成
                step_id = self.task_planner.current_step - 1
                self.task_planner.mark_step_completed(step_id, result)
                
                if result.get("success", False):
                    logger.info(f"步骤执行成功: {next_step['description']}")
                else:
                    logger.warning(f"步骤执行失败: {result.get('error', 'Unknown error')}")
                
            except Exception as e:
                error_msg = f"步骤执行失败: {str(e)}"
                logger.error(error_msg)
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
        
        logger.info(f"任务执行完成: {final_result['summary']}")
        return final_result
    
    async def _execute_agent_step(self, agent_input: Dict[str, Any]) -> Dict[str, Any]:
        """执行单个agent步骤"""
        step_info = agent_input.get("task_step", {})
        step_type = step_info.get("type", "unknown")
        step_title = step_info.get("title", "未命名步骤")
        
        logger.debug(f"开始执行Agent步骤: {step_type}")
        llm_agent_logger.info("=" * 60)
        llm_agent_logger.info(f"🤖 开始执行Agent步骤: {step_title}")
        llm_agent_logger.info("=" * 60)
        llm_agent_logger.info(f"📋 步骤类型: {step_type}")
        llm_agent_logger.info(f"📝 步骤描述: {step_info.get('description', '无描述')}")
        llm_agent_logger.info(f"🔧 预期工具: {', '.join(step_info.get('tools', []))}")
        llm_agent_logger.info(f"⏱️ 预估时间: {step_info.get('estimated_time', '未知')}")
        
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
            
            logger.debug("构建Agent状态完成，开始调用Agent")
            llm_agent_logger.info("🧠 开始调用LLM Agent...")
            llm_agent_logger.info(f"💬 用户输入: {agent_input['input'][:150]}{'...' if len(agent_input['input']) > 150 else ''}")
            
            # 调用agent执行
            result = await self.agent.ainvoke(state)
            
            logger.debug("Agent调用完成，解析结果")
            llm_agent_logger.info("✅ LLM Agent响应完成，开始解析结果...")
            
            # 统计消息数量
            message_count = len(result.get("messages", []))
            llm_agent_logger.info(f"📨 消息总数: {message_count}")
            
            # 解析agent的响应
            if "messages" in result and len(result["messages"]) > 1:
                # 分析所有消息的思考过程
                llm_agent_logger.info("🧭 Agent思考过程分析:")
                
                for i, message in enumerate(result["messages"]):
                    message_type = message.get("type", "unknown")
                    message_name = getattr(message, 'name', None) or message.get("name", "unknown")
                    
                    if message_type == "human":
                        llm_agent_logger.info(f"  {i+1}. [用户] {message_name}: {message.get('content', '')[:100]}{'...' if len(message.get('content', '')) > 100 else ''}")
                    elif message_type == "ai":
                        content = message.get('content', '')
                        tool_calls = getattr(message, 'tool_calls', []) or message.get('tool_calls', [])
                        
                        llm_agent_logger.info(f"  {i+1}. [AI] {message_name}:")
                        if content:
                            llm_agent_logger.info(f"     💭 思考: {content[:200]}{'...' if len(content) > 200 else ''}")
                        
                        if tool_calls:
                            llm_agent_logger.info(f"     🔧 工具调用: {len(tool_calls)} 个")
                            for j, tool_call in enumerate(tool_calls):
                                tool_name = tool_call.get('name', 'unknown')
                                tool_args = tool_call.get('args', {})
                                llm_agent_logger.info(f"        {j+1}. {tool_name}: {str(tool_args)[:100]}{'...' if len(str(tool_args)) > 100 else ''}")
                    elif message_type == "tool":
                        tool_name = message_name
                        tool_content = message.get('content', '')
                        llm_agent_logger.info(f"  {i+1}. [工具] {tool_name}: {tool_content[:150]}{'...' if len(tool_content) > 150 else ''}")
                
                # 获取最后的AI响应
                last_message = result["messages"][-1]
                output = last_message.get("content", "No output")
                
                # 检查是否有工具调用
                tool_calls = getattr(last_message, 'tool_calls', []) or last_message.get('tool_calls', [])
                if tool_calls:
                    logger.info(f"Agent调用了 {len(tool_calls)} 个工具")
                    llm_agent_logger.info(f"🛠️ 最终工具调用统计: {len(tool_calls)} 个工具")
                    
                    for i, tool_call in enumerate(tool_calls):
                        tool_name = tool_call.get('name', 'unknown')
                        logger.debug(f"工具调用 {i+1}: {tool_name}")
                        llm_agent_logger.info(f"   {i+1}. {tool_name}")
                else:
                    logger.debug("Agent没有调用工具")
                    llm_agent_logger.info("🛠️ 未调用任何工具")
                
                # 记录最终输出
                llm_agent_logger.info("📋 最终输出:")
                llm_agent_logger.info(f"   {output[:300]}{'...' if len(output) > 300 else ''}")
                    
            else:
                output = "Agent执行完成，但没有返回具体输出"
                logger.warning("Agent返回的消息格式异常")
                llm_agent_logger.warning("⚠️ Agent返回的消息格式异常")
            
            
            result_data = {
                "success": True,
                "step_type": step_info.get("type", "unknown"),
                "description": step_info.get("description", ""),
                "tools_used": step_info.get("tools", []),
                "iteration": agent_input.get("iteration", 0),
                "output": output,
                "agent_result": result
            }
            
            logger.info(f"Agent步骤执行成功: {step_type}")
            llm_agent_logger.info(f"✅ Agent步骤 '{step_title}' 执行成功")
            llm_agent_logger.info("=" * 60)
            
            return result_data
            
        except Exception as e:
            logger.error(f"Agent步骤执行失败: {str(e)}")
            llm_agent_logger.error(f"❌ Agent步骤 '{step_title}' 执行失败: {str(e)}")
            llm_agent_logger.info("=" * 60)
            
            return {
                "success": False,
                "error": str(e),
                "step_type": step_info.get("type", "unknown")
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