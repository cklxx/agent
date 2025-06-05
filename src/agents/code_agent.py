# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
Code Agent module for handling coding tasks with planning and tool usage capabilities.
"""

from typing import List, Dict, Any, Optional
from langgraph.prebuilt import create_react_agent
from src.llms.llm import get_llm_by_type
from src.config.agents import AGENT_LLM_MAP


class CodeTaskPlanner:
    """处理代码任务的规划和拆解"""
    
    def __init__(self):
        self.tasks = []
        self.current_step = 0
    
    def plan_task(self, description: str) -> List[Dict[str, Any]]:
        """
        将复杂的代码任务拆解为可执行的步骤
        
        Args:
            description: 任务描述
            
        Returns:
            List of task steps with details
        """
        # 基于任务描述生成执行计划
        plan = self._analyze_task(description)
        self.tasks = plan
        return plan
    
    def _analyze_task(self, description: str) -> List[Dict[str, Any]]:
        """分析任务并生成详细的执行计划"""
        # 简化版的任务分析逻辑
        # 在实际实现中，这里应该使用LLM来分析任务
        steps = []
        
        # 检查是否需要文件操作
        if "文件" in description or "代码" in description:
            steps.append({
                "type": "file_analysis",
                "description": "分析现有文件结构",
                "tools": ["file_reader", "directory_scanner"],
                "priority": 1
            })
        
        # 检查是否需要命令行操作
        if "运行" in description or "执行" in description or "命令" in description:
            steps.append({
                "type": "command_execution",
                "description": "执行命令行操作",
                "tools": ["terminal_executor"],
                "priority": 2
            })
        
        # 检查是否需要代码修改
        if "修改" in description or "更新" in description or "实现" in description:
            steps.append({
                "type": "code_modification",
                "description": "修改或实现代码",
                "tools": ["file_writer", "diff_generator"],
                "priority": 3
            })
        
        return steps
    
    def get_next_step(self) -> Optional[Dict[str, Any]]:
        """获取下一个执行步骤"""
        if self.current_step < len(self.tasks):
            step = self.tasks[self.current_step]
            self.current_step += 1
            return step
        return None
    
    def mark_step_completed(self, step_id: int, result: Any):
        """标记步骤完成"""
        if step_id < len(self.tasks):
            self.tasks[step_id]["completed"] = True
            self.tasks[step_id]["result"] = result


def create_code_agent(tools: List[Any]) -> Any:
    """
    创建代码处理专用的agent
    
    Args:
        tools: 可用的工具列表
        
    Returns:
        Configured code agent
    """
    prompt_template = """
    你是一个专业的代码助手，具备以下能力：
    1. 代码任务规划和拆解
    2. 文件读取和写入
    3. 命令行执行
    4. 代码diff和增量更新
    
    请根据用户的需求，合理使用提供的工具来完成任务。
    在执行任务前，请先制定详细的执行计划。
    
    当前任务：{input}
    
    可用工具：{tools}
    
    请按照以下步骤执行：
    1. 分析任务需求
    2. 制定执行计划
    3. 按步骤执行
    4. 验证结果
    """
    
    return create_react_agent(
        name="code_agent",
        model=get_llm_by_type(AGENT_LLM_MAP.get("researcher", "anthropic_claude_3_5_sonnet")),
        tools=tools,
        prompt=prompt_template,
    ) 