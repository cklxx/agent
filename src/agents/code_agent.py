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
llm_planner_logger = logging.getLogger("code_agent_llm_planner")


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
        logger.info(
            f"📋 开始任务规划: {description[:50]}{'...' if len(description) > 50 else ''}"
        )
        llm_planner_logger.info(
            f"🚀 任务描述: {description[:100]}{'...' if len(description) > 100 else ''}"
        )

        # 基于任务描述生成执行计划
        plan = self._analyze_task(description)
        self.tasks = plan

        logger.info(f"✅ 规划完成，生成 {len(plan)} 个步骤")

        # 只在debug模式下显示详细步骤
        for i, step in enumerate(plan, 1):
            logger.debug(f"  步骤 {i}: {step['type']} - {step['description']}")

        return plan

    def _analyze_task(self, description: str) -> List[Dict[str, Any]]:
        """分析任务并生成详细的执行计划"""
        logger.debug("开始LLM任务分析...")

        # 使用LLM进行智能任务分析
        try:
            llm = get_llm_by_type("reasoning")
            llm_planner_logger.info(f"🧠 LLM分析中...")

            # 构建状态用于apply_prompt_template
            prompt_state = {"messages": [], "task_description": description}

            # 使用apply_prompt_template统一管理prompt
            messages = apply_prompt_template("code_agent_task_analyzer", prompt_state)

            response = llm.invoke(messages)
            llm_response = (
                response.content if hasattr(response, "content") else str(response)
            )

            # 尝试解析LLM返回的JSON
            try:
                # 清理可能的格式问题
                clean_response = llm_response.strip()
                if clean_response.startswith("```json"):
                    clean_response = clean_response[7:]
                if clean_response.endswith("```"):
                    clean_response = clean_response[:-3]
                clean_response = clean_response.strip()

                plan_data = json.loads(clean_response)

                # 验证计划结构
                if "phases" not in plan_data:
                    raise ValueError("计划缺少phases字段")

                phases = plan_data["phases"]
                llm_planner_logger.info(f"📝 生成 {len(phases)} 个执行阶段")

                # 转换为扁平化的步骤列表，保持阶段信息
                converted_steps = []
                step_counter = 1

                for phase in phases:
                    phase_name = phase.get("phase", "unknown")
                    phase_desc = phase.get("description", "")
                    steps = phase.get("steps", [])

                    logger.debug(f"处理阶段: {phase_name} - {phase_desc}")

                    for step in steps:
                        converted_step = {
                            "id": step_counter,
                            "phase": phase_name,
                            "phase_description": phase_desc,
                            "type": step.get("type", "general_task"),
                            "title": step.get("title", "未命名步骤"),
                            "description": step.get("description", "未设置描述"),
                            "tools": step.get("tools", []),
                            "priority": step.get("priority", 1),
                            "estimated_time": step.get("estimated_time", "2-5分钟"),
                            "verification_criteria": step.get(
                                "verification_criteria", []
                            ),
                            "task_analysis": plan_data.get("task_analysis", ""),
                            "execution_strategy": plan_data.get(
                                "execution_strategy", ""
                            ),
                        }
                        converted_steps.append(converted_step)
                        step_counter += 1

                # 记录生成的计划摘要
                llm_planner_logger.info(
                    f"✅ 生成完整执行计划: {len(converted_steps)} 个步骤"
                )

                # 只在debug模式下显示详细信息
                if converted_steps:
                    logger.debug("详细计划概览:")
                    current_phase = None
                    for step in converted_steps:
                        if step["phase"] != current_phase:
                            current_phase = step["phase"]
                            logger.debug(f"\n🔹 阶段: {current_phase.upper()}")

                        logger.debug(
                            f"  {step['id']}. [{step['type']}] {step['title']}"
                        )
                        logger.debug(
                            f"     📖 {step['description'][:50]}{'...' if len(step['description']) > 50 else ''}"
                        )
                        if step["verification_criteria"]:
                            logger.debug(
                                f"     ✅ 验证: {', '.join(step['verification_criteria'][:2])}"
                            )

                # 记录完整的规划JSON（调试模式）
                logger.debug("完整规划JSON:")
                logger.debug(json.dumps(plan_data, indent=2, ensure_ascii=False))

                llm_planner_logger.info("✅ 增强规划解析成功")
                return converted_steps

            except (json.JSONDecodeError, ValueError) as e:
                logger.debug(f"LLM规划解析失败: {str(e)}")
                llm_planner_logger.warning("🔄 回退到增强规则分析")

        except Exception as e:
            logger.debug(f"LLM任务分析失败: {str(e)}")
            llm_planner_logger.warning("🔄 回退到增强规则分析")

        # 增强的基于规则的分析方法
        logger.debug("使用增强的基于规则的任务分析方法")

        # 阶段1: 前置信息收集步骤
        pre_analysis_steps = [
            {
                "id": 1,
                "phase": "pre_analysis",
                "phase_description": "前置信息收集阶段",
                "type": "environment_assessment",
                "title": "环境评估",
                "description": "获取当前工作目录和探索项目结构",
                "tools": ["get_current_directory", "list_directory_contents"],
                "priority": 1,
                "estimated_time": "1-2分钟",
                "verification_criteria": ["确认工作目录", "了解项目结构"],
            },
            {
                "id": 2,
                "phase": "pre_analysis",
                "phase_description": "前置信息收集阶段",
                "type": "context_analysis",
                "title": "上下文分析",
                "description": "分析相关文件和代码结构，理解现有实现",
                "tools": ["read_file", "get_file_info"],
                "priority": 2,
                "estimated_time": "2-3分钟",
                "verification_criteria": ["理解代码结构", "确认依赖关系"],
            },
        ]

        # 阶段2: 实施步骤（基于任务类型动态生成）
        implementation_steps = []
        step_id = 3

        # 检查任务类型并生成对应的实施步骤
        if any(
            keyword in description.lower()
            for keyword in ["文件", "代码", "create", "modify", "implement"]
        ):
            implementation_steps.append(
                {
                    "id": step_id,
                    "phase": "implementation",
                    "phase_description": "任务实施阶段",
                    "type": "code_implementation",
                    "title": "代码实现",
                    "description": "实现或修改代码功能",
                    "tools": ["write_file", "create_new_file", "append_to_file"],
                    "priority": 1,
                    "estimated_time": "5-15分钟",
                    "verification_criteria": ["代码语法正确", "功能符合要求"],
                }
            )
            step_id += 1

        if any(
            keyword in description.lower()
            for keyword in ["运行", "执行", "test", "command", "install"]
        ):
            implementation_steps.append(
                {
                    "id": step_id,
                    "phase": "implementation",
                    "phase_description": "任务实施阶段",
                    "type": "command_execution",
                    "title": "命令执行",
                    "description": "执行必要的命令行操作",
                    "tools": ["execute_terminal_command"],
                    "priority": 2,
                    "estimated_time": "2-5分钟",
                    "verification_criteria": ["命令成功执行", "输出符合预期"],
                }
            )
            step_id += 1

        # 如果没有识别到特定类型，添加通用实施步骤
        if not implementation_steps:
            implementation_steps.append(
                {
                    "id": step_id,
                    "phase": "implementation",
                    "phase_description": "任务实施阶段",
                    "type": "general_implementation",
                    "title": "任务实施",
                    "description": "执行主要任务内容",
                    "tools": ["all_available"],
                    "priority": 1,
                    "estimated_time": "5-10分钟",
                    "verification_criteria": ["任务目标达成"],
                }
            )
            step_id += 1

        # 阶段3: 验证步骤
        verification_steps = [
            {
                "id": step_id,
                "phase": "verification",
                "phase_description": "验证确认阶段",
                "type": "file_verification",
                "title": "文件完整性验证",
                "description": "验证文件创建/修改是否正确，检查内容完整性",
                "tools": ["get_file_info", "read_file", "generate_file_diff"],
                "priority": 1,
                "estimated_time": "1-2分钟",
                "verification_criteria": ["文件存在", "内容正确", "权限合适"],
            },
            {
                "id": step_id + 1,
                "phase": "verification",
                "phase_description": "验证确认阶段",
                "type": "functional_testing",
                "title": "功能测试",
                "description": "测试实现功能的正确性和稳定性",
                "tools": ["execute_terminal_command"],
                "priority": 2,
                "estimated_time": "2-3分钟",
                "verification_criteria": ["功能正常", "无错误", "性能可接受"],
            },
            {
                "id": step_id + 2,
                "phase": "verification",
                "phase_description": "验证确认阶段",
                "type": "integration_verification",
                "title": "集成验证",
                "description": "验证新实现与现有系统的兼容性",
                "tools": ["execute_terminal_command", "read_file"],
                "priority": 3,
                "estimated_time": "1-2分钟",
                "verification_criteria": ["无兼容问题", "现有功能完好"],
            },
        ]

        # 合并所有步骤
        all_steps = pre_analysis_steps + implementation_steps + verification_steps

        # 记录增强分析结果
        logger.debug("增强规则分析结果:")
        current_phase = None
        for step in all_steps:
            if step["phase"] != current_phase:
                current_phase = step["phase"]
                logger.debug(f"\n🔹 阶段: {current_phase.upper()}")

            logger.debug(f"  {step['id']}. [{step['type']}] {step['title']}")
            logger.debug(
                f"     📖 {step['description'][:50]}{'...' if len(step['description']) > 50 else ''}"
            )

        llm_planner_logger.info(f"✅ 增强规则分析完成: {len(all_steps)} 个步骤")
        return all_steps

    def get_next_step(self) -> Optional[Dict[str, Any]]:
        """获取下一个执行步骤"""
        if self.current_step < len(self.tasks):
            step = self.tasks[self.current_step]
            logger.info(
                f"获取步骤 {self.current_step + 1}/{len(self.tasks)}: {step['type']}"
            )
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
    tool_names = [getattr(tool, "name", str(tool)) for tool in tools]
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
