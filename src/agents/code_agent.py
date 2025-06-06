# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
Code Agent module for handling coding tasks with planning and tool usage capabilities.
"""

import logging
import json
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

# 设置LLM规划日志
llm_planner_logger = logging.getLogger("code_agent_llm_planner")
llm_planner_logger.setLevel(logging.INFO)

# 如果没有handler，添加一个console handler
if not llm_planner_logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('🧠 [LLM] %(asctime)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S')
    console_handler.setFormatter(formatter)
    llm_planner_logger.addHandler(console_handler)


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
        llm_planner_logger.info("🚀 开始Code Agent任务规划")
        llm_planner_logger.info(f"📝 任务描述: {description}")
        
        # 基于任务描述生成执行计划
        plan = self._analyze_task(description)
        self.tasks = plan
        
        logger.info(f"任务规划完成，生成 {len(plan)} 个步骤")
        llm_planner_logger.info(f"✅ 任务规划完成，共生成 {len(plan)} 个执行步骤")
        
        for i, step in enumerate(plan, 1):
            logger.debug(f"步骤 {i}: {step['type']} - {step['description']}")
        
        return plan
    
    def _analyze_task(self, description: str) -> List[Dict[str, Any]]:
        """分析任务并生成详细的执行计划"""
        logger.debug("分析任务内容...")
        llm_planner_logger.info("🤔 开始智能分析任务...")
        
        # 使用LLM进行智能任务分析
        try:
            llm = get_llm_by_type("reasoning")
            llm_planner_logger.info(f"🧠 使用LLM模型: {getattr(llm, 'model_name', 'unknown')}")
            
            # 构建任务分析的提示
            analysis_prompt = f"""
你是一个专业的代码任务规划助手。请分析以下任务描述，并生成详细的执行计划。

任务描述：{description}

请生成一个JSON格式的执行计划，包含以下字段：
{{
    "analysis": "任务分析和理解",
    "approach": "解决方案和方法",
    "steps": [
        {{
            "type": "步骤类型（如：file_analysis, command_execution, code_modification等）",
            "title": "步骤标题",
            "description": "详细描述",
            "tools": ["需要的工具列表"],
            "priority": 优先级数字,
            "estimated_time": "预估时间"
        }}
    ]
}}

请确保：
1. 步骤逻辑清晰，按照依赖关系排序
2. 每个步骤都有明确的目标和可执行的操作
3. 工具选择合适，符合实际需求
4. 步骤数量适中（3-8个步骤为宜）

输出纯JSON格式，不要包含任何其他文本。
"""

            llm_planner_logger.info("📤 发送任务分析请求到LLM...")
            response = llm.invoke(analysis_prompt)
            llm_response = response.content if hasattr(response, 'content') else str(response)
            
            llm_planner_logger.info("📥 收到LLM规划响应")
            llm_planner_logger.info("=" * 60)
            llm_planner_logger.info("🧠 LLM任务规划详情:")
            llm_planner_logger.info("=" * 60)
            
            # 尝试解析LLM返回的JSON
            try:
                # 清理可能的格式问题
                clean_response = llm_response.strip()
                if clean_response.startswith('```json'):
                    clean_response = clean_response[7:]
                if clean_response.endswith('```'):
                    clean_response = clean_response[:-3]
                clean_response = clean_response.strip()
                
                plan_data = json.loads(clean_response)
                
                # 记录LLM分析结果
                llm_planner_logger.info(f"🔍 任务分析: {plan_data.get('analysis', '未提供')}")
                llm_planner_logger.info(f"💡 解决方案: {plan_data.get('approach', '未提供')}")
                
                steps = plan_data.get('steps', [])
                llm_planner_logger.info(f"📋 规划步骤数量: {len(steps)}")
                
                if steps:
                    llm_planner_logger.info("📝 详细步骤列表:")
                    for i, step in enumerate(steps, 1):
                        step_type = step.get('type', '未知')
                        title = step.get('title', '未设置标题')
                        description = step.get('description', '未设置描述')
                        tools = step.get('tools', [])
                        priority = step.get('priority', 0)
                        estimated_time = step.get('estimated_time', '未预估')
                        
                        llm_planner_logger.info(f"  {i}. [{step_type.upper()}] {title}")
                        llm_planner_logger.info(f"     📖 描述: {description}")
                        llm_planner_logger.info(f"     🔧 工具: {', '.join(tools) if tools else '无特定工具'}")
                        llm_planner_logger.info(f"     ⭐ 优先级: {priority}")
                        llm_planner_logger.info(f"     ⏱️ 预估时间: {estimated_time}")
                        
                        if i < len(steps):  # 不是最后一个步骤
                            llm_planner_logger.info("     " + "-" * 50)
                
                # 记录完整的规划JSON（调试模式）
                llm_planner_logger.debug("🔧 完整规划JSON:")
                llm_planner_logger.debug(json.dumps(plan_data, indent=2, ensure_ascii=False))
                
                llm_planner_logger.info("=" * 60)
                
                # 转换为内部格式
                converted_steps = []
                for step in steps:
                    converted_steps.append({
                        "type": step.get('type', 'general_analysis'),
                        "title": step.get('title', '未命名步骤'),
                        "description": step.get('description', '未设置描述'),
                        "tools": step.get('tools', []),
                        "priority": step.get('priority', 1),
                        "estimated_time": step.get('estimated_time', '未知'),
                        "analysis": plan_data.get('analysis', ''),
                        "approach": plan_data.get('approach', '')
                    })
                
                llm_planner_logger.info("✅ LLM规划解析成功，已转换为执行格式")
                return converted_steps
                
            except json.JSONDecodeError as e:
                llm_planner_logger.error(f"❌ LLM规划解析失败: {str(e)}")
                llm_planner_logger.error(f"原始LLM响应: {llm_response[:300]}{'...' if len(llm_response) > 300 else ''}")
                llm_planner_logger.warning("🔄 回退到基于规则的任务分析")
                
        except Exception as e:
            llm_planner_logger.error(f"❌ LLM任务分析失败: {str(e)}")
            llm_planner_logger.warning("🔄 回退到基于规则的任务分析")
        
        # 回退到基于规则的简化分析
        llm_planner_logger.info("🔧 使用基于规则的任务分析方法")
        steps = []
        
        # 检查是否需要文件操作
        if "文件" in description or "代码" in description or "file" in description.lower():
            steps.append({
                "type": "file_analysis",
                "title": "文件分析",
                "description": "分析现有文件结构和代码内容",
                "tools": ["file_reader", "directory_scanner"],
                "priority": 1,
                "estimated_time": "1-2分钟"
            })
            logger.debug("检测到文件操作需求")
        
        # 检查是否需要命令行操作
        if "运行" in description or "执行" in description or "命令" in description or "command" in description.lower() or "list" in description.lower():
            steps.append({
                "type": "command_execution",
                "title": "命令执行",
                "description": "执行必要的命令行操作",
                "tools": ["terminal_executor"],
                "priority": 2,
                "estimated_time": "1-3分钟"
            })
            logger.debug("检测到命令行操作需求")
        
        # 检查是否需要代码修改
        if "修改" in description or "更新" in description or "实现" in description or "create" in description.lower() or "modify" in description.lower():
            steps.append({
                "type": "code_modification",
                "title": "代码修改",
                "description": "修改或实现代码功能",
                "tools": ["file_writer", "diff_generator"],
                "priority": 3,
                "estimated_time": "3-10分钟"
            })
            logger.debug("检测到代码修改需求")
        
        # 如果没有检测到特定操作，添加通用分析步骤
        if not steps:
            steps.append({
                "type": "general_analysis",
                "title": "通用任务分析",
                "description": "通用任务分析和执行",
                "tools": ["all_available"],
                "priority": 1,
                "estimated_time": "2-5分钟"
            })
            logger.debug("未检测到特定操作，使用通用分析")
        
        # 记录基于规则的分析结果
        llm_planner_logger.info("📋 基于规则的分析结果:")
        for i, step in enumerate(steps, 1):
            llm_planner_logger.info(f"  {i}. [{step['type'].upper()}] {step['title']}")
            llm_planner_logger.info(f"     📖 {step['description']}")
            llm_planner_logger.info(f"     ⏱️ 预估时间: {step['estimated_time']}")
        
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