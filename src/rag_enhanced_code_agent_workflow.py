# SPDX-License-Identifier: MIT

"""
RAG增强Code Agent工作流 - 集成context和RAG功能的完整工作流
"""

import asyncio
import logging
from typing import List, Dict, Any

from src.agents.rag_enhanced_code_agent import (
    create_rag_enhanced_code_agent,
)
from src.tools import (
    execute_terminal_command,
    get_current_directory,
    list_directory_contents,
    read_file,
    read_file_lines,
    get_file_info,
    write_file,
    append_to_file,
    create_new_file,
    generate_file_diff,
)

# 设置日志
logger = logging.getLogger(__name__)


class RAGEnhancedCodeAgentWorkflow:
    """RAG增强的代码代理工作流"""

    def __init__(self, repo_path: str = "."):
        """初始化RAG增强代码代理工作流"""
        logger.info("初始化RAG增强代码代理工作流")

        self.repo_path = repo_path

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

        # 创建RAG增强的code agent
        try:
            self.agent = create_rag_enhanced_code_agent(
                repo_path=repo_path, tools=self.code_tools
            )
            logger.info("RAG增强代码代理创建成功")
        except Exception as e:
            logger.error(f"创建RAG增强代码代理失败: {str(e)}")
            raise

    async def execute_task(
        self, task_description: str, max_iterations: int = 5
    ) -> Dict[str, Any]:
        """
        执行RAG增强的代码任务

        Args:
            task_description: 任务描述
            max_iterations: 最大执行轮次

        Returns:
            任务执行结果
        """
        logger.info(f"🚀 开始执行RAG增强代码任务")
        logger.info(
            f"📋 任务描述: {task_description[:100]}{'...' if len(task_description) > 100 else ''}"
        )

        try:
            # 使用RAG增强agent执行任务
            result = await self.agent.execute_task_with_rag(
                task_description=task_description, max_iterations=max_iterations
            )

            # 增强结果信息
            enhanced_result = self._enhance_result(result, task_description)

            # 记录执行结果
            if enhanced_result.get("success"):
                logger.info("🎉 RAG增强任务执行成功!")
            else:
                logger.warning("⚠️ RAG增强任务执行部分成功或失败")

            success_count = enhanced_result.get("successful_steps", 0)
            total_steps = enhanced_result.get("total_steps", 0)
            relevant_files = enhanced_result.get("relevant_files_analyzed", 0)

            logger.info(f"📈 执行统计: {success_count}/{total_steps} 步骤成功")
            logger.info(f"🔍 RAG分析: {relevant_files} 个相关文件")

            return enhanced_result

        except Exception as e:
            logger.error(f"❌ RAG增强任务执行失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "rag_enhanced": True,
                "workflow_type": "rag_enhanced",
            }

    def _enhance_result(
        self, result: Dict[str, Any], task_description: str
    ) -> Dict[str, Any]:
        """增强执行结果信息"""
        enhanced = {
            **result,
            "workflow_type": "rag_enhanced",
            "repo_path": self.repo_path,
            "task_description": task_description,
            "enhancement_features": [
                "RAG代码检索",
                "上下文感知规划",
                "模式一致性验证",
                "智能代码生成",
            ],
        }

        # 添加质量指标
        if result.get("results"):
            rag_enhanced_steps = sum(
                1 for r in result["results"] if r.get("rag_enhanced", False)
            )
            enhanced["rag_enhancement_rate"] = (
                rag_enhanced_steps / len(result["results"]) if result["results"] else 0
            )

        return enhanced

    async def analyze_codebase(self) -> Dict[str, Any]:
        """分析代码库结构和模式"""
        logger.info("🔍 开始分析代码库...")

        try:
            # 使用agent的内部组件进行分析
            task_planner = self.agent.task_planner

            # 分析项目结构
            project_info = await task_planner._analyze_project_structure()

            # 检索关键代码模式（使用通用查询）
            common_patterns = await task_planner._retrieve_relevant_code(
                "class function implementation pattern"
            )

            analysis_result = {
                "project_structure": project_info,
                "common_patterns": common_patterns,
                "analysis_timestamp": asyncio.get_event_loop().time(),
                "repo_path": self.repo_path,
            }

            logger.info(f"✅ 代码库分析完成")
            logger.info(f"   📁 总文件数: {project_info.get('total_files', 0)}")
            logger.info(
                f"   🔤 主要语言: {', '.join(project_info.get('main_languages', [])[:3])}"
            )
            logger.info(f"   📋 发现模式: {len(common_patterns)} 个")

            return analysis_result

        except Exception as e:
            logger.error(f"❌ 代码库分析失败: {str(e)}")
            return {"success": False, "error": str(e)}

    async def suggest_improvements(self, focus_area: str = "") -> Dict[str, Any]:
        """基于RAG分析建议代码改进"""
        logger.info("💡 生成代码改进建议...")

        try:
            # 构建改进建议任务
            improvement_task = f"""
            基于当前代码库的分析，请提供代码改进建议。
            {'重点关注: ' + focus_area if focus_area else ''}
            
            请分析:
            1. 代码结构和架构改进机会
            2. 性能优化建议
            3. 可维护性提升方案
            4. 安全性增强建议
            5. 测试覆盖率改进
            """

            # 执行分析任务
            result = await self.execute_task(improvement_task)

            if result.get("success"):
                logger.info("✅ 改进建议生成成功")
            else:
                logger.warning("⚠️ 改进建议生成部分成功")

            return result

        except Exception as e:
            logger.error(f"❌ 改进建议生成失败: {str(e)}")
            return {"success": False, "error": str(e)}

    async def execute_refactoring(
        self, target_files: List[str], refactoring_goals: str
    ) -> Dict[str, Any]:
        """执行代码重构任务"""
        logger.info(f"🔄 开始代码重构...")
        logger.info(
            f"📁 目标文件: {', '.join(target_files[:3])}{'...' if len(target_files) > 3 else ''}"
        )

        try:
            # 构建重构任务
            refactoring_task = f"""
            请对以下文件进行重构:
            {chr(10).join(f"- {file}" for file in target_files)}
            
            重构目标:
            {refactoring_goals}
            
            要求:
            1. 保持现有功能完整性
            2. 遵循项目代码风格和模式
            3. 提高代码可读性和可维护性
            4. 确保向后兼容性
            5. 添加必要的测试验证
            """

            # 执行重构任务
            result = await self.execute_task(refactoring_task)

            # 增强重构结果
            if result.get("success"):
                result["refactoring_files"] = target_files
                result["refactoring_goals"] = refactoring_goals
                logger.info("✅ 代码重构完成")
            else:
                logger.warning("⚠️ 代码重构部分完成")

            return result

        except Exception as e:
            logger.error(f"❌ 代码重构失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "refactoring_files": target_files,
            }

    async def generate_documentation(self, doc_type: str = "api") -> Dict[str, Any]:
        """生成项目文档"""
        logger.info(f"📚 开始生成 {doc_type} 文档...")

        try:
            # 构建文档生成任务
            if doc_type.lower() == "api":
                doc_task = """
                基于当前代码库生成API文档:
                1. 分析所有公开的类和函数
                2. 提取文档字符串和注释
                3. 生成结构化的API文档
                4. 包含使用示例和参数说明
                5. 遵循项目文档风格
                """
            elif doc_type.lower() == "architecture":
                doc_task = """
                生成项目架构文档:
                1. 分析项目整体结构
                2. 识别核心组件和依赖关系
                3. 生成架构图和说明
                4. 描述设计模式和最佳实践
                5. 包含部署和配置说明
                """
            else:
                doc_task = f"""
                生成 {doc_type} 相关文档:
                1. 分析相关代码和组件
                2. 提取关键信息和模式
                3. 生成结构化文档
                4. 包含示例和最佳实践
                """

            # 执行文档生成任务
            result = await self.execute_task(doc_task)

            if result.get("success"):
                result["documentation_type"] = doc_type
                logger.info(f"✅ {doc_type} 文档生成完成")
            else:
                logger.warning(f"⚠️ {doc_type} 文档生成部分完成")

            return result

        except Exception as e:
            logger.error(f"❌ 文档生成失败: {str(e)}")
            return {"success": False, "error": str(e), "documentation_type": doc_type}

    def get_available_tools(self) -> List[str]:
        """获取可用工具列表"""
        return [getattr(tool, "name", str(tool)) for tool in self.code_tools]

    def get_workflow_capabilities(self) -> Dict[str, Any]:
        """获取工作流能力描述"""
        return {
            "core_features": [
                "RAG增强代码生成",
                "上下文感知任务规划",
                "模式一致性保证",
                "智能代码重构",
                "自动文档生成",
            ],
            "supported_tasks": [
                "新功能开发",
                "代码重构",
                "Bug修复",
                "性能优化",
                "文档生成",
                "架构分析",
            ],
            "quality_metrics": ["模式一致性", "代码重用率", "集成质量", "约定遵循率"],
            "tools_count": len(self.code_tools),
            "repo_path": self.repo_path,
        }


# 异步运行函数
async def run_rag_enhanced_code_agent_workflow(
    task_description: str, repo_path: str = ".", max_iterations: int = 5
) -> Dict[str, Any]:
    """
    运行RAG增强的代码代理工作流

    Args:
        task_description: 任务描述
        repo_path: 代码仓库路径
        max_iterations: 最大迭代次数

    Returns:
        任务执行结果
    """
    workflow = RAGEnhancedCodeAgentWorkflow(repo_path)
    return await workflow.execute_task(task_description, max_iterations)


# 同步包装函数
def run_rag_enhanced_code_agent_workflow_sync(
    task_description: str, repo_path: str = ".", max_iterations: int = 5
) -> Dict[str, Any]:
    """
    同步运行RAG增强的代码代理工作流

    Args:
        task_description: 任务描述
        repo_path: 代码仓库路径
        max_iterations: 最大迭代次数

    Returns:
        任务执行结果
    """
    return asyncio.run(
        run_rag_enhanced_code_agent_workflow(
            task_description, repo_path, max_iterations
        )
    )
