# SPDX-License-Identifier: MIT

"""
RAG增强的Code Agent - 集成context管理和代码检索功能
"""

import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from langgraph.prebuilt import create_react_agent
from src.llms.llm import get_llm_by_type
from src.prompts import apply_prompt_template

# RAG组件
from src.rag.code_retriever import CodeRetriever

# Context组件
from src.context.manager import ContextManager
from src.context.base import ContextType, Priority

logger = logging.getLogger(__name__)


class RAGEnhancedCodeTaskPlanner:
    """增强的代码任务规划器，集成RAG和Context功能"""

    def __init__(
        self, repo_path: str = ".", context_manager: Optional[ContextManager] = None
    ):
        self.repo_path = repo_path
        self.context_manager = context_manager or ContextManager()

        # 初始化RAG组件
        self.code_retriever = CodeRetriever(repo_path)
        self.code_indexer = self.code_retriever.indexer

        self.tasks = []
        self.current_step = 0

        # 存储相关上下文信息
        self.relevant_code_contexts: List[Dict[str, Any]] = []
        self.project_structure: Dict[str, Any] = {}

        logger.info("Initializing RAG-enhanced task planner")

    async def plan_task_with_context(self, description: str) -> List[Dict[str, Any]]:
        """
        基于RAG和Context信息进行任务规划

        Args:
            description: 任务描述

        Returns:
            增强的任务步骤列表
        """
        logger.info(f"🧠 Starting RAG-based task planning: {description[:50]}...")

        # 1. 添加任务到context管理器
        task_context_id = await self.context_manager.add_context(
            content=description,
            context_type=ContextType.TASK,
            metadata={"task_type": "code_task", "status": "planning"},
            priority=Priority.HIGH,
            tags=["code_task", "planning"],
        )

        # 2. 使用RAG检索相关代码信息
        relevant_code = await self._retrieve_relevant_code(description)

        # 3. 分析项目结构
        project_info = await self._analyze_project_structure()

        # 4. 基于检索到的信息生成增强的规划
        enhanced_plan = await self._generate_enhanced_plan(
            description, relevant_code, project_info
        )

        # 5. 将规划信息添加到context
        await self.context_manager.add_context(
            content={
                "plan": enhanced_plan,
                "relevant_code": relevant_code,
                "project_info": project_info,
            },
            context_type=ContextType.PLANNING,
            metadata={"task_id": task_context_id},
            priority=Priority.HIGH,
            tags=["code_plan", "rag_enhanced"],
        )

        self.tasks = enhanced_plan
        logger.info(
            f"✅ RAG-enhanced planning completed, generated {len(enhanced_plan)} steps"
        )

        return enhanced_plan

    async def _retrieve_relevant_code(self, description: str) -> List[Dict[str, Any]]:
        """检索与任务相关的代码"""
        logger.info("🔍 Retrieving relevant code...")

        try:
            # 使用代码检索器搜索相关文档
            documents = self.code_retriever.query_relevant_documents(description)

            relevant_code = []
            for doc in documents:
                code_info = {
                    "file_path": doc.id,
                    "title": doc.title,
                    "url": doc.url,
                    "chunks": [],
                }

                for chunk in doc.chunks:
                    code_info["chunks"].append(
                        {"content": chunk.content, "similarity": chunk.similarity}
                    )

                relevant_code.append(code_info)

            logger.info(f"✅ Found {len(relevant_code)} relevant code files")
            self.relevant_code_contexts = relevant_code

            return relevant_code

        except Exception as e:
            logger.error(f"❌ Failed to retrieve relevant code: {str(e)}")
            return []

    async def _analyze_project_structure(self) -> Dict[str, Any]:
        """分析项目结构"""
        logger.info("📊 Analyzing project structure...")

        try:
            # 获取索引器统计信息
            stats = self.code_indexer.get_statistics()

            # 扫描仓库文件
            all_files = self.code_indexer.scan_repository()

            project_info = {
                "total_files": stats.get("total_files", 0),
                "files_by_language": stats.get("files_by_language", {}),
                "total_chunks": stats.get("total_chunks", 0),
                "recent_files": all_files[:20] if all_files else [],
                "main_languages": list(stats.get("files_by_language", {}).keys())[:5],
            }

            self.project_structure = project_info
            logger.info(
                f"✅ Project analysis completed: {project_info['total_files']} files"
            )

            return project_info

        except Exception as e:
            logger.error(f"❌ Project structure analysis failed: {str(e)}")
            return {}

    async def _generate_enhanced_plan(
        self,
        description: str,
        relevant_code: List[Dict[str, Any]],
        project_info: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """生成增强的执行计划"""
        logger.info("⚡ Generating enhanced execution plan...")

        # 基础计划结构
        base_plan = [
            {
                "id": 1,
                "phase": "context_analysis",
                "phase_description": "上下文分析阶段",
                "type": "rag_context_analysis",
                "title": "RAG上下文分析",
                "description": "基于RAG检索分析相关代码和项目结构",
                "tools": ["code_retriever", "context_manager"],
                "priority": 1,
                "estimated_time": "2-3分钟",
                "verification_criteria": ["理解相关代码", "把握项目架构"],
                "rag_context": {
                    "relevant_files": [code["file_path"] for code in relevant_code],
                    "project_languages": project_info.get("main_languages", []),
                    "total_context_files": len(relevant_code),
                },
            },
            {
                "id": 2,
                "phase": "environment_setup",
                "phase_description": "环境准备阶段",
                "type": "enhanced_environment_assessment",
                "title": "增强环境评估",
                "description": "结合RAG信息进行环境评估和准备",
                "tools": [
                    "get_current_directory",
                    "list_directory_contents",
                    "get_file_info",
                ],
                "priority": 2,
                "estimated_time": "1-2分钟",
                "verification_criteria": ["确认工作环境", "验证依赖项"],
                "context_hints": [
                    f"项目包含 {project_info.get('total_files', 0)} 个文件",
                    f"主要语言: {', '.join(project_info.get('main_languages', [])[:3])}",
                    f"找到 {len(relevant_code)} 个相关文件",
                ],
            },
        ]

        # 根据任务类型和相关代码生成具体实施步骤
        implementation_steps = await self._generate_implementation_steps(
            description, relevant_code, project_info
        )

        # 增强验证步骤
        verification_steps = [
            {
                "id": len(base_plan) + len(implementation_steps) + 1,
                "phase": "rag_verification",
                "phase_description": "RAG增强验证阶段",
                "type": "context_aware_verification",
                "title": "上下文感知验证",
                "description": "基于相关代码上下文验证实现正确性",
                "tools": ["read_file", "generate_file_diff", "context_manager"],
                "priority": 1,
                "estimated_time": "2-4分钟",
                "verification_criteria": [
                    "代码风格一致性",
                    "与现有架构兼容",
                    "依赖关系正确",
                ],
                "rag_validation": {
                    "check_against_similar_code": True,
                    "verify_patterns": True,
                    "validate_imports": True,
                },
            }
        ]

        # 合并所有步骤
        all_steps = base_plan + implementation_steps + verification_steps

        # 为每个步骤添加RAG上下文信息
        for step in all_steps:
            step["rag_enhanced"] = True
            step["available_context"] = {
                "relevant_files_count": len(relevant_code),
                "project_languages": project_info.get("main_languages", []),
                "has_similar_implementations": len(relevant_code) > 0,
            }

        return all_steps

    async def _generate_implementation_steps(
        self,
        description: str,
        relevant_code: List[Dict[str, Any]],
        project_info: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """生成具体的实施步骤"""
        steps = []
        step_id = 3  # 继续base_plan的编号

        # 分析任务类型
        task_lower = description.lower()

        if any(
            keyword in task_lower for keyword in ["create", "new", "implement", "add"]
        ):
            # 创建新功能的步骤
            steps.append(
                {
                    "id": step_id,
                    "phase": "implementation",
                    "phase_description": "实现阶段",
                    "type": "rag_guided_implementation",
                    "title": "RAG指导的代码实现",
                    "description": "基于相关代码模式和项目结构实现新功能",
                    "tools": ["write_file", "create_new_file", "read_file"],
                    "priority": 1,
                    "estimated_time": "10-20分钟",
                    "verification_criteria": ["功能完整", "遵循项目模式", "代码规范"],
                    "implementation_hints": self._get_implementation_hints(
                        relevant_code
                    ),
                    "similar_implementations": len(relevant_code),
                }
            )
            step_id += 1

        if any(
            keyword in task_lower for keyword in ["modify", "update", "change", "fix"]
        ):
            # 修改现有代码的步骤
            steps.append(
                {
                    "id": step_id,
                    "phase": "implementation",
                    "phase_description": "实现阶段",
                    "type": "context_aware_modification",
                    "title": "上下文感知的代码修改",
                    "description": "基于相关代码上下文进行安全修改",
                    "tools": ["read_file", "write_file", "generate_file_diff"],
                    "priority": 1,
                    "estimated_time": "5-15分钟",
                    "verification_criteria": ["修改准确", "保持兼容性", "无破坏性变更"],
                    "modification_context": {
                        "related_files": [code["file_path"] for code in relevant_code],
                        "impact_analysis_required": True,
                    },
                }
            )
            step_id += 1

        if any(keyword in task_lower for keyword in ["test", "debug", "validate"]):
            # 测试和调试步骤
            steps.append(
                {
                    "id": step_id,
                    "phase": "implementation",
                    "phase_description": "实现阶段",
                    "type": "rag_enhanced_testing",
                    "title": "RAG增强测试",
                    "description": "基于相关代码模式进行全面测试",
                    "tools": ["execute_terminal_command", "read_file"],
                    "priority": 2,
                    "estimated_time": "5-10分钟",
                    "verification_criteria": ["测试通过", "覆盖关键场景", "性能可接受"],
                    "testing_patterns": self._extract_testing_patterns(relevant_code),
                }
            )

        # 如果没有匹配到特定类型，添加通用实施步骤
        if not steps:
            steps.append(
                {
                    "id": step_id,
                    "phase": "implementation",
                    "phase_description": "实现阶段",
                    "type": "generic_rag_implementation",
                    "title": "通用RAG实现",
                    "description": "基于检索到的相关信息执行任务",
                    "tools": ["all_available"],
                    "priority": 1,
                    "estimated_time": "10-15分钟",
                    "verification_criteria": ["任务完成", "质量达标"],
                    "context_guidance": f"找到 {len(relevant_code)} 个相关参考",
                }
            )

        return steps

    def _get_implementation_hints(
        self, relevant_code: List[Dict[str, Any]]
    ) -> List[str]:
        """从相关代码中提取实现提示"""
        hints = []

        for code_info in relevant_code:
            file_path = code_info["file_path"]
            chunks = code_info.get("chunks", [])

            # 分析文件类型和模式
            if file_path.endswith(".py"):
                hints.append(f"参考 {Path(file_path).name} 中的Python实现模式")
            elif file_path.endswith((".js", ".ts")):
                hints.append(
                    f"参考 {Path(file_path).name} 中的JavaScript/TypeScript模式"
                )

            # 从高相似度的代码块中提取模式
            high_similarity_chunks = [
                chunk for chunk in chunks if chunk.get("similarity", 0) > 0.7
            ]

            if high_similarity_chunks:
                hints.append(f"在 {Path(file_path).name} 中发现高度相关的实现")

        return hints[:5]  # 限制提示数量

    def _extract_testing_patterns(
        self, relevant_code: List[Dict[str, Any]]
    ) -> List[str]:
        """从相关代码中提取测试模式"""
        patterns = []

        for code_info in relevant_code:
            file_path = code_info["file_path"]

            if "test" in file_path.lower():
                patterns.append(f"参考 {Path(file_path).name} 中的测试模式")

            # 检查是否有pytest、unittest等测试框架的使用
            chunks = code_info.get("chunks", [])
            for chunk in chunks:
                content = chunk.get("content", "").lower()
                if "pytest" in content:
                    patterns.append("使用pytest测试框架")
                elif "unittest" in content:
                    patterns.append("使用unittest测试框架")
                elif "test_" in content:
                    patterns.append("遵循test_前缀命名约定")

        return list(set(patterns))  # 去重

    async def get_context_for_step(self, step_id: int) -> Dict[str, Any]:
        """为特定步骤获取相关上下文"""
        if step_id >= len(self.tasks):
            return {}

        step = self.tasks[step_id]
        context = {
            "step_info": step,
            "relevant_code": self.relevant_code_contexts,
            "project_structure": self.project_structure,
        }

        # 从context管理器获取相关历史上下文
        related_contexts = await self.context_manager.search_contexts(
            query=step.get("title", ""), context_type=ContextType.TASK, limit=3
        )

        context["historical_context"] = [
            {"content": ctx.content, "metadata": ctx.metadata}
            for ctx in related_contexts
        ]

        return context


class RAGEnhancedCodeAgent:
    """RAG增强的代码代理"""

    def __init__(self, repo_path: str = ".", tools: Optional[List[Any]] = None):
        self.repo_path = repo_path
        self.tools = tools or []

        # 初始化增强组件
        self.context_manager = ContextManager()
        self.task_planner = RAGEnhancedCodeTaskPlanner(repo_path, self.context_manager)

        # 创建基础agent
        self.agent = self._create_agent()

        logger.info("RAG Enhanced Code Agent initialization completed")

    def _create_agent(self):
        """创建RAG增强的代理"""
        try:
            llm = get_llm_by_type("reasoning")

            agent = create_react_agent(
                name="rag_enhanced_code_agent",
                model=llm,
                tools=self.tools,
                prompt=lambda state: self._apply_rag_enhanced_prompt(state),
            )

            return agent

        except Exception as e:
            logger.error(f"Failed to create RAG Enhanced Code Agent: {str(e)}")
            raise

    def _apply_rag_enhanced_prompt(self, state: Dict[str, Any]) -> List[Dict[str, str]]:
        """应用RAG增强的提示模板"""

        # 获取RAG上下文信息
        rag_context = state.get("rag_context", {})
        relevant_code = rag_context.get("relevant_code", [])
        project_info = rag_context.get("project_structure", {})

        # 构建增强的状态信息
        enhanced_state = {
            **state,
            "rag_context_available": len(relevant_code) > 0,
            "relevant_files_count": len(relevant_code),
            "project_languages": project_info.get("main_languages", []),
            "has_context_manager": True,
        }

        # 使用RAG增强的提示模板
        base_messages = apply_prompt_template("rag_enhanced_code_agent", enhanced_state)

        # 添加RAG特定的系统提示
        if relevant_code:
            rag_prompt = self._build_rag_context_prompt(relevant_code, project_info)
            base_messages.insert(1, {"role": "system", "content": rag_prompt})

        return base_messages

    def _build_rag_context_prompt(
        self, relevant_code: List[Dict[str, Any]], project_info: Dict[str, Any]
    ) -> str:
        """构建RAG上下文提示"""

        prompt_parts = [
            "# RAG增强上下文信息",
            "",
            f"你现在拥有以下相关代码上下文信息，请充分利用这些信息来更好地完成任务：",
            "",
            "## 项目概况",
            f"- 总文件数: {project_info.get('total_files', 0)}",
            f"- 主要编程语言: {', '.join(project_info.get('main_languages', []))}",
            f"- 找到相关文件: {len(relevant_code)} 个",
            "",
        ]

        if relevant_code:
            prompt_parts.extend(["## 相关代码文件", ""])

            for i, code_info in enumerate(relevant_code[:5], 1):  # 限制显示前5个
                file_path = code_info["file_path"]
                chunks = code_info.get("chunks", [])

                prompt_parts.append(f"### {i}. {Path(file_path).name}")
                prompt_parts.append(f"**文件路径**: {file_path}")

                if chunks:
                    high_similarity = [
                        c for c in chunks if c.get("similarity", 0) > 0.6
                    ]
                    if high_similarity:
                        prompt_parts.append(
                            f"**相关度**: 高 ({len(high_similarity)} 个高相关代码块)"
                        )
                        prompt_parts.append("**相关代码片段**:")
                        prompt_parts.append("```")
                        # 显示最相关的代码片段
                        best_chunk = max(
                            high_similarity, key=lambda x: x.get("similarity", 0)
                        )
                        content = (
                            best_chunk["content"][:500] + "..."
                            if len(best_chunk["content"]) > 500
                            else best_chunk["content"]
                        )
                        prompt_parts.append(content)
                        prompt_parts.append("```")
                    else:
                        prompt_parts.append(f"**相关度**: 中等")

                prompt_parts.append("")

        prompt_parts.extend(
            [
                "## RAG增强指导原则",
                "",
                "1. **模式复用**: 参考相关代码中的实现模式和最佳实践",
                "2. **一致性**: 保持与现有代码风格和架构的一致性",
                "3. **依赖管理**: 注意现有的依赖关系和导入方式",
                "4. **命名约定**: 遵循项目中已有的命名约定",
                "5. **错误处理**: 参考相关代码中的错误处理方式",
                "",
                "请在执行任务时充分考虑上述上下文信息，确保你的实现与现有代码库保持高度一致。",
            ]
        )

        return "\n".join(prompt_parts)

    async def execute_task_with_rag(
        self, task_description: str, max_iterations: int = 5
    ) -> Dict[str, Any]:
        """使用RAG增强执行任务"""
        logger.info("🚀 Starting RAG Enhanced task execution")

        try:
            # 1. 使用RAG进行任务规划
            plan = await self.task_planner.plan_task_with_context(task_description)

            if not plan:
                return {"success": False, "error": "RAG增强任务规划失败", "results": []}

            # 2. 执行任务步骤
            results = []
            for i, step in enumerate(plan):
                logger.info(f"📋 Executing step {i+1}/{len(plan)}: {step['title']}")

                # 获取步骤相关上下文
                step_context = await self.task_planner.get_context_for_step(i)

                # 构建agent输入状态
                agent_state = {
                    "messages": [
                        {
                            "role": "user",
                            "content": self._build_step_prompt(
                                step, step_context, task_description
                            ),
                        }
                    ],
                    "rag_context": step_context,
                    "current_step": step,
                    "step_index": i,
                }

                # 执行agent步骤
                try:
                    step_result = await self.agent.ainvoke(agent_state)

                    # 处理结果
                    result = {
                        "step_id": i,
                        "step_title": step["title"],
                        "success": True,
                        "result": step_result,
                        "rag_enhanced": True,
                    }

                    # 将结果添加到context管理器
                    await self.context_manager.add_context(
                        content=result,
                        context_type=ContextType.EXECUTION_RESULT,
                        metadata={"step_id": i, "task_type": "code_task"},
                        priority=Priority.MEDIUM,
                        tags=["execution_result", "rag_enhanced"],
                    )

                    results.append(result)
                    logger.info(f"✅ Step {i+1} executed successfully")

                except Exception as e:
                    logger.error(f"❌ Step {i+1} execution failed: {str(e)}")
                    results.append(
                        {
                            "step_id": i,
                            "step_title": step["title"],
                            "success": False,
                            "error": str(e),
                            "rag_enhanced": True,
                        }
                    )

            # 3. 生成最终结果
            success_count = sum(1 for r in results if r.get("success", False))
            overall_success = success_count == len(results)

            final_result = {
                "success": overall_success,
                "total_steps": len(plan),
                "successful_steps": success_count,
                "results": results,
                "rag_enhanced": True,
                "context_used": True,
                "relevant_files_analyzed": len(
                    self.task_planner.relevant_code_contexts
                ),
            }

            # 将最终结果添加到context
            await self.context_manager.add_context(
                content=final_result,
                context_type=ContextType.TASK_RESULT,
                metadata={"task_description": task_description},
                priority=Priority.HIGH,
                tags=["final_result", "rag_enhanced", "code_task"],
            )

            logger.info(
                f"🎉 RAG Enhanced task execution completed: {success_count}/{len(plan)} steps successful"
            )

            return final_result

        except Exception as e:
            logger.error(f"❌ RAG Enhanced task execution failed: {str(e)}")
            return {"success": False, "error": str(e), "rag_enhanced": True}

    def _build_step_prompt(
        self, step: Dict[str, Any], step_context: Dict[str, Any], original_task: str
    ) -> str:
        """为特定步骤构建提示"""

        prompt_parts = [
            f"# 任务执行 - {step['title']}",
            "",
            f"**原始任务**: {original_task}",
            f"**当前步骤**: {step['description']}",
            f"**执行阶段**: {step['phase_description']}",
            f"**预计用时**: {step.get('estimated_time', '未知')}",
            "",
        ]

        # 添加RAG上下文信息
        relevant_code = step_context.get("relevant_code", [])
        if relevant_code:
            prompt_parts.extend(
                [
                    "## 相关代码上下文",
                    f"找到 {len(relevant_code)} 个相关文件供参考：",
                    "",
                ]
            )

            for code_info in relevant_code[:3]:  # 限制显示前3个最相关的
                prompt_parts.append(
                    f"- **{Path(code_info['file_path']).name}**: {code_info['file_path']}"
                )

        # 添加项目结构信息
        project_info = step_context.get("project_structure", {})
        if project_info:
            prompt_parts.extend(
                [
                    "",
                    "## 项目结构信息",
                    f"- 项目文件总数: {project_info.get('total_files', 0)}",
                    f"- 主要编程语言: {', '.join(project_info.get('main_languages', [])[:3])}",
                    "",
                ]
            )

        # 添加特定步骤的提示
        if step.get("rag_enhanced"):
            prompt_parts.extend(["## RAG增强指导", "请根据上述相关代码上下文信息："])

            if step.get("implementation_hints"):
                prompt_parts.extend(
                    ["### 实现提示"]
                    + [f"- {hint}" for hint in step["implementation_hints"]]
                )

            if step.get("context_hints"):
                prompt_parts.extend(
                    ["### 上下文提示"] + [f"- {hint}" for hint in step["context_hints"]]
                )

        # 添加验证标准
        if step.get("verification_criteria"):
            prompt_parts.extend(
                ["", "## 验证标准", "完成后请确保满足以下标准："]
                + [f"- {criteria}" for criteria in step["verification_criteria"]]
            )

        prompt_parts.extend(["", "请开始执行这个步骤，并充分利用提供的上下文信息。"])

        return "\n".join(prompt_parts)


# 工厂函数
def create_rag_enhanced_code_agent(
    repo_path: str = ".", tools: Optional[List[Any]] = None
) -> RAGEnhancedCodeAgent:
    """
    创建RAG增强的代码代理

    Args:
        repo_path: 工作区代码路径
        tools: 可用工具列表

    Returns:
        RAG增强的代码代理实例
    """
    logger.info(f"Creating RAG Enhanced Code Agent - repository path: {repo_path}")

    return RAGEnhancedCodeAgent(repo_path=repo_path, tools=tools)


# 异步运行函数
async def run_rag_enhanced_code_agent(
    task_description: str,
    repo_path: str = ".",
    tools: Optional[List[Any]] = None,
    max_iterations: int = 5,
) -> Dict[str, Any]:
    """
    运行RAG增强的代码代理任务

    Args:
        task_description: 任务描述
        repo_path: 代码仓库路径
        tools: 可用工具列表
        max_iterations: 最大迭代次数

    Returns:
        任务执行结果
    """
    agent = create_rag_enhanced_code_agent(repo_path, tools)
    return await agent.execute_task_with_rag(task_description, max_iterations)
