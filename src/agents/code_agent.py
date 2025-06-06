# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
Code Agent module for handling coding tasks with planning and tool usage capabilities.
"""

import logging
from typing import List, Dict, Any, Optional
from langgraph.prebuilt import create_react_agent
from src.llms.llm import get_llm_by_type
from src.config.agents import AGENT_LLM_MAP
from src.prompts import apply_prompt_template

# 设置日志
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 如果没有handler，添加一个console handler
if not logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('🤖 [CodeAgent] %(asctime)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)


class CodeTaskPlanner:
    """处理代码任务的规划和拆解"""
    
    def __init__(self):
        self.tasks = []
        self.current_step = 0
        logger.info("初始化任务规划器")
    
    def plan_task(self, description: str) -> List[Dict[str, Any]]:
        """
        将复杂的代码任务拆解为可执行的步骤
        
        Args:
            description: 任务描述
            
        Returns:
            List of task steps with details
        """
        logger.info(f"开始规划任务: {description[:50]}{'...' if len(description) > 50 else ''}")
        
        # 基于任务描述生成执行计划
        plan = self._analyze_task(description)
        self.tasks = plan
        
        logger.info(f"任务规划完成，生成 {len(plan)} 个步骤")
        for i, step in enumerate(plan, 1):
            logger.debug(f"步骤 {i}: {step['type']} - {step['description']}")
        
        return plan
    
    def _analyze_task(self, description: str) -> List[Dict[str, Any]]:
        """分析任务并生成详细的执行计划"""
        logger.debug("分析任务内容...")
        
        # 简化版的任务分析逻辑
        # 在实际实现中，这里应该使用LLM来分析任务
        steps = []
        
        # 检查是否需要文件操作
        if "文件" in description or "代码" in description or "file" in description.lower():
            steps.append({
                "type": "file_analysis",
                "description": "分析现有文件结构",
                "tools": ["file_reader", "directory_scanner"],
                "priority": 1
            })
            logger.debug("检测到文件操作需求")
        
        # 检查是否需要命令行操作
        if "运行" in description or "执行" in description or "命令" in description or "command" in description.lower() or "list" in description.lower():
            steps.append({
                "type": "command_execution",
                "description": "执行命令行操作",
                "tools": ["terminal_executor"],
                "priority": 2
            })
            logger.debug("检测到命令行操作需求")
        
        # 检查是否需要代码修改
        if "修改" in description or "更新" in description or "实现" in description or "create" in description.lower() or "modify" in description.lower():
            steps.append({
                "type": "code_modification",
                "description": "修改或实现代码",
                "tools": ["file_writer", "diff_generator"],
                "priority": 3
            })
            logger.debug("检测到代码修改需求")
        
        # 如果没有检测到特定操作，添加通用分析步骤
        if not steps:
            steps.append({
                "type": "general_analysis",
                "description": "通用任务分析和执行",
                "tools": ["all_available"],
                "priority": 1
            })
            logger.debug("未检测到特定操作，使用通用分析")
        
        return steps
    
    def get_next_step(self) -> Optional[Dict[str, Any]]:
        """获取下一个执行步骤"""
        if self.current_step < len(self.tasks):
            step = self.tasks[self.current_step]
            logger.info(f"获取步骤 {self.current_step + 1}/{len(self.tasks)}: {step['type']}")
            self.current_step += 1
            return step
        logger.info("所有步骤已完成")
        return None
    
    def mark_step_completed(self, step_id: int, result: Any):
        """标记步骤完成"""
        if step_id < len(self.tasks):
            self.tasks[step_id]["completed"] = True
            self.tasks[step_id]["result"] = result
            logger.info(f"步骤 {step_id + 1} 标记为已完成")
        else:
            logger.warning(f"尝试标记无效步骤 {step_id + 1} 为已完成")


def create_code_agent(tools: List[Any]) -> Any:
    """
    创建代码处理专用的agent
    
    Args:
        tools: 可用的工具列表
        
    Returns:
        Configured code agent
    """
    logger.info(f"创建Code Agent，配置 {len(tools)} 个工具")
    
    # 记录工具名称
    tool_names = [getattr(tool, 'name', str(tool)) for tool in tools]
    logger.debug(f"可用工具: {', '.join(tool_names)}")
    
    try:
        # 获取LLM
        llm = get_llm_by_type("reasoning")
        logger.info(f"使用LLM模型: {getattr(llm, 'model_name', 'unknown')}")
        
        # 创建agent
        agent = create_react_agent(
            name="code_agent",
            model=llm,
            tools=tools,
            prompt=lambda state: apply_prompt_template("code_agent", state),
        )
        
        logger.info("Code Agent 创建成功")
        return agent
        
    except Exception as e:
        logger.error(f"创建Code Agent失败: {str(e)}")
        raise 