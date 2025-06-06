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
llm_agent_logger = logging.getLogger("code_agent_llm_execution")


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
        执行代码任务，支持三阶段执行模式：
        1. 前置信息收集阶段
        2. 任务实施阶段  
        3. 验证确认阶段
        
        Args:
            task_description: 任务描述
            max_iterations: 最大执行轮次
            
        Returns:
            任务执行结果
        """
        logger.info(f"🚀 开始执行代码任务")
        logger.info(f"📋 任务描述: {task_description[:100]}{'...' if len(task_description) > 100 else ''}")
        
        # 1. 任务规划阶段
        logger.info("📋 阶段1: 任务规划...")
        plan = self.task_planner.plan_task(task_description)
        
        if not plan:
            return {"success": False, "error": "任务规划失败", "results": []}
        
        # 按阶段组织步骤
        phases = {}
        for step in plan:
            phase = step.get('phase', 'unknown')
            if phase not in phases:
                phases[phase] = []
            phases[phase].append(step)
        
        logger.info(f"📊 规划完成: {len(phases)} 个阶段，共 {len(plan)} 个步骤")
        for phase_name, phase_steps in phases.items():
            logger.info(f"  🔹 {phase_name}: {len(phase_steps)} 个步骤")
        
        # 2. 分阶段执行
        results = []
        overall_success = True
        phase_results = {}
        
        # 执行前置信息收集阶段
        if 'pre_analysis' in phases:
            logger.info("\n🔍 阶段2: 前置信息收集...")
            phase_result = await self._execute_phase("pre_analysis", phases['pre_analysis'], task_description)
            phase_results['pre_analysis'] = phase_result
            results.extend(phase_result['step_results'])
            
            if not phase_result['success']:
                logger.error("❌ 前置信息收集失败，终止执行")
                overall_success = False
                return self._build_final_result(results, overall_success, "前置信息收集失败")
            
            logger.info(f"✅ 前置信息收集完成: {phase_result['success_count']}/{phase_result['total_steps']} 步骤成功")
        
        # 执行任务实施阶段
        if 'implementation' in phases and overall_success:
            logger.info("\n⚙️ 阶段3: 任务实施...")
            phase_result = await self._execute_phase("implementation", phases['implementation'], task_description)
            phase_results['implementation'] = phase_result
            results.extend(phase_result['step_results'])
            
            if not phase_result['success']:
                logger.warning("⚠️ 任务实施阶段有问题，但继续验证阶段")
                overall_success = False
            else:
                logger.info(f"✅ 任务实施完成: {phase_result['success_count']}/{phase_result['total_steps']} 步骤成功")
        
        # 执行验证确认阶段
        if 'verification' in phases:
            logger.info("\n🔬 阶段4: 验证确认...")
            phase_result = await self._execute_phase("verification", phases['verification'], task_description)
            phase_results['verification'] = phase_result
            results.extend(phase_result['step_results'])
            
            if not phase_result['success']:
                logger.error("❌ 验证阶段失败")
                overall_success = False
            else:
                logger.info(f"✅ 验证确认完成: {phase_result['success_count']}/{phase_result['total_steps']} 步骤成功")
        
        # 3. 汇总结果
        final_result = self._build_final_result(results, overall_success, "任务执行完成")
        final_result['phase_results'] = phase_results
        final_result['phases_executed'] = list(phases.keys())
        
        # 记录最终状态
        success_count = sum(1 for r in results if r.get("success", False))
        total_steps = len(results)
        
        if overall_success:
            logger.info(f"🎉 任务执行成功完成!")
        else:
            logger.warning(f"⚠️ 任务执行部分成功")
            
        logger.info(f"📈 执行统计: {success_count}/{total_steps} 步骤成功")
        logger.info(f"🔹 执行阶段: {', '.join(phases.keys())}")
        
        return final_result
    
    async def _execute_phase(self, phase_name: str, phase_steps: List[Dict[str, Any]], task_description: str) -> Dict[str, Any]:
        """
        执行特定阶段的所有步骤
        
        Args:
            phase_name: 阶段名称
            phase_steps: 阶段包含的步骤列表
            task_description: 原始任务描述
            
        Returns:
            阶段执行结果
        """
        logger.debug(f"开始执行阶段: {phase_name}")
        step_results = []
        success_count = 0
        phase_success = True
        
        for i, step in enumerate(phase_steps, 1):
            step_id = step.get('id', i)
            step_title = step.get('title', '未命名步骤')
            step_desc = step.get('description', '')
            verification_criteria = step.get('verification_criteria', [])
            
            logger.info(f"📋 步骤 {step_id}: {step_title}")
            if verification_criteria:
                logger.debug(f"   ✅ 验证标准: {', '.join(verification_criteria)}")
            
            # 构建agent输入，包含阶段上下文
            agent_input = {
                "input": f"""任务: {task_description}

当前阶段: {phase_name} - {step.get('phase_description', '')}
当前步骤: {step_title}
步骤描述: {step_desc}
可用工具: {step.get('tools', [])}
验证标准: {verification_criteria}

请按照以下要求执行:
1. 明确说明你正在执行哪个阶段的哪个步骤
2. 使用合适的工具完成步骤目标
3. 根据验证标准检查执行结果
4. 如果是验证阶段，详细报告验证结果""",
                "task_step": step,
                "phase": phase_name,
                "step_number": f"{step_id}/{len(phase_steps)}",
                "verification_criteria": verification_criteria
            }
            
            try:
                # 执行agent步骤
                result = await self._execute_agent_step(agent_input)
                step_results.append(result)
                
                # 检查步骤执行结果
                if result.get("success", False):
                    success_count += 1
                    logger.info(f"  ✅ 步骤 {step_id} 完成")
                    
                    # 对于验证阶段，进行额外的验证检查
                    if phase_name == "verification":
                        verification_passed = await self._validate_step_result(step, result)
                        if not verification_passed:
                            logger.warning(f"  ⚠️ 步骤 {step_id} 验证未完全通过")
                            result['verification_warning'] = True
                else:
                    logger.warning(f"  ❌ 步骤 {step_id} 失败: {result.get('error', 'Unknown error')[:50]}{'...' if len(result.get('error', '')) > 50 else ''}")
                    phase_success = False
                
                # 标记步骤完成
                self.task_planner.mark_step_completed(step_id - 1, result)
                
            except Exception as e:
                error_msg = f"步骤 {step_id} 执行异常: {str(e)}"
                logger.error(f"  ❌ {error_msg}")
                step_results.append({
                    "success": False, 
                    "error": error_msg,
                    "step_id": step_id,
                    "step_title": step_title,
                    "phase": phase_name
                })
                phase_success = False
        
        phase_result = {
            "phase": phase_name,
            "success": phase_success,
            "success_count": success_count,
            "total_steps": len(phase_steps),
            "step_results": step_results
        }
        
        logger.debug(f"阶段 {phase_name} 执行完成: {success_count}/{len(phase_steps)} 步骤成功")
        return phase_result
    
    async def _validate_step_result(self, step: Dict[str, Any], result: Dict[str, Any]) -> bool:
        """
        验证步骤执行结果是否符合预期
        
        Args:
            step: 步骤信息
            result: 执行结果
            
        Returns:
            验证是否通过
        """
        verification_criteria = step.get('verification_criteria', [])
        if not verification_criteria:
            return True  # 没有验证标准则认为通过
        
        step_type = step.get('type', '')
        logger.debug(f"验证步骤类型: {step_type}")
        
        # 基于步骤类型进行特定验证
        try:
            if step_type == "file_verification":
                # 验证文件相关操作
                return await self._validate_file_operations(result)
            elif step_type == "functional_testing":
                # 验证功能测试结果
                return await self._validate_functional_tests(result)
            elif step_type == "integration_verification":
                # 验证集成测试结果
                return await self._validate_integration_tests(result)
            else:
                # 通用验证：检查是否有明显的错误信息
                output = result.get('output', '')
                return 'error' not in output.lower() and 'failed' not in output.lower()
                
        except Exception as e:
            logger.debug(f"验证过程异常: {e}")
            return False
    
    async def _validate_file_operations(self, result: Dict[str, Any]) -> bool:
        """验证文件操作结果"""
        # 检查agent输出中是否包含文件操作成功的标志
        output = result.get('output', '').lower()
        success_indicators = ['文件创建成功', '文件修改成功', '文件存在', 'successfully', 'created', 'modified']
        error_indicators = ['文件不存在', '权限不足', 'permission denied', 'file not found', 'failed']
        
        has_success = any(indicator in output for indicator in success_indicators)
        has_error = any(indicator in output for indicator in error_indicators)
        
        return has_success and not has_error
    
    async def _validate_functional_tests(self, result: Dict[str, Any]) -> bool:
        """验证功能测试结果"""
        output = result.get('output', '').lower()
        success_indicators = ['测试通过', '功能正常', 'test passed', 'ok', 'success']
        error_indicators = ['测试失败', '错误', 'test failed', 'error', 'exception']
        
        has_success = any(indicator in output for indicator in success_indicators)
        has_error = any(indicator in output for indicator in error_indicators)
        
        return has_success and not has_error
    
    async def _validate_integration_tests(self, result: Dict[str, Any]) -> bool:
        """验证集成测试结果"""
        output = result.get('output', '').lower()
        success_indicators = ['集成成功', '兼容', 'integration successful', 'compatible']
        error_indicators = ['冲突', '不兼容', 'conflict', 'incompatible']
        
        has_success = any(indicator in output for indicator in success_indicators)
        has_error = any(indicator in output for indicator in error_indicators)
        
        return has_success and not has_error
    
    def _build_final_result(self, results: List[Dict[str, Any]], success: bool, message: str) -> Dict[str, Any]:
        """构建最终执行结果"""
        success_count = sum(1 for r in results if r.get("success", False))
        total_steps = len(results)
        
        return {
            "success": success,
            "message": message,
            "total_steps": total_steps,
            "successful_steps": success_count,
            "failed_steps": total_steps - success_count,
            "success_rate": f"{success_count}/{total_steps}" if total_steps > 0 else "0/0",
            "results": results,
            "summary": {
                "task_completed": success,
                "all_phases_executed": True,
                "verification_performed": any(r.get('step_type') == 'verification' for r in results)
            }
        }
    
    async def _execute_agent_step(self, agent_input: Dict[str, Any]) -> Dict[str, Any]:
        """执行单个agent步骤"""
        step_info = agent_input.get("task_step", {})
        step_type = step_info.get("type", "unknown")
        step_title = step_info.get("title", "未命名步骤")
        
        logger.debug(f"开始执行Agent步骤: {step_type}")
        llm_agent_logger.info(f"🤖 执行: {step_title}")
        
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
            
            logger.debug("调用LLM Agent...")
            
            # 调用agent执行
            result = await self.agent.ainvoke(state)
            
            logger.debug("Agent响应完成，解析结果...")
            
            # 统计消息数量
            message_count = len(result.get("messages", []))
            logger.debug(f"消息总数: {message_count}")
            
            # 解析agent的响应
            if "messages" in result and len(result["messages"]) > 1:
                # 获取最后的AI响应
                last_message = result["messages"][-1]
                output = last_message.get("content", "No output")
                
                # 检查是否有工具调用
                tool_calls = getattr(last_message, 'tool_calls', []) or last_message.get('tool_calls', [])
                if tool_calls:
                    tool_names = [tool_call.get('name', 'unknown') for tool_call in tool_calls]
                    logger.info(f"  🔧 使用工具: {', '.join(tool_names)}")
                else:
                    logger.debug("未调用工具")
                
                # 简化的最终输出记录
                if output and len(output.strip()) > 0:
                    logger.debug(f"Agent输出: {output[:100]}{'...' if len(output) > 100 else ''}")
                    
            else:
                output = "Agent执行完成，但没有返回具体输出"
                logger.warning("Agent返回的消息格式异常")
            
            
            result_data = {
                "success": True,
                "step_type": step_info.get("type", "unknown"),
                "description": step_info.get("description", ""),
                "tools_used": step_info.get("tools", []),
                "iteration": agent_input.get("iteration", 0),
                "output": output,
                "agent_result": result
            }
            
            logger.debug(f"Agent步骤执行成功: {step_type}")
            
            return result_data
            
        except Exception as e:
            logger.error(f"Agent步骤执行失败: {str(e)}")
            llm_agent_logger.error(f"❌ 步骤失败: {str(e)[:50]}{'...' if len(str(e)) > 50 else ''}")
            
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