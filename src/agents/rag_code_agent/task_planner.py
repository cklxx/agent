


import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from src.llms.llm import get_llm_by_type

# Enhanced RAG components
from src.rag.enhanced_retriever import EnhancedRAGRetriever
from src.rag.code_retriever import CodeRetriever
from src.rag.code_indexer import CodeIndexer

# Context components
from src.context.manager import ContextManager
from src.context.base import ContextType, Priority
from src.context.intelligent_workspace_analyzer import IntelligentWorkspaceAnalyzer


logger = logging.getLogger(__name__)
class RAGEnhancedCodeTaskPlanner:
    """
    RAG Enhanced Code Task Planner with pre-decision analysis architecture
    """

    def __init__(
        self,
        repo_path: str = ".",
        context_manager: Optional[ContextManager] = None,
        use_enhanced_retriever: bool = True,
        embedding_config: Optional[Dict[str, Any]] = None,
    ):
        self.repo_path = Path(repo_path)
        self.use_enhanced_retriever = use_enhanced_retriever
        
        # Initialize workspace analyzer for intelligent decisions
        self.workspace_analyzer = IntelligentWorkspaceAnalyzer(repo_path)
        
        # Initialize context manager
        self.context_manager = context_manager or ContextManager()
        
        # Initialize RAG components
        if use_enhanced_retriever:
            try:
                self.rag_retriever = EnhancedRAGRetriever(
                    repo_path=repo_path, embedding_config=embedding_config
                )
                logger.info("Enhanced RAG Retriever initialized successfully")
            except Exception as e:
                logger.warning(f"Enhanced RAG Retriever initialization failed: {e}")
                logger.info("Falling back to basic code retriever")
                self.rag_retriever = CodeRetriever(repo_path=repo_path)
                self.use_enhanced_retriever = False
        else:
            self.rag_retriever = CodeRetriever(repo_path=repo_path)
        
        # Initialize code indexer for project analysis
        self.code_indexer = CodeIndexer(repo_path, use_intelligent_filter=True)
        
        # Store contexts
        self.tasks = []
        self.relevant_code_contexts = []
        self.project_info = {}
        self.decision_context = {}

    async def pre_decision_analysis(self, description: str) -> Dict[str, Any]:
        """
        Pre-task decision analysis (1st model call)
        Separated from task planning for better architecture
        """
        logger.info(f"🧠 执行预先决策分析: {description[:50]}...")

        # 1. Add task to context manager
        task_context_id = await self.context_manager.add_context(
            content=description,
            context_type=ContextType.TASK,
            metadata={
                "task_type": "code_task",
                "status": "analyzing",
                "enhanced_rag": self.use_enhanced_retriever,
            },
            priority=Priority.HIGH,
            tags=["code_task", "analysis"],
        )

        # 2. Intelligent decision on whether to perform analysis and indexing
        should_analyze_env, should_build_rag, decision_context = await self.workspace_analyzer.should_perform_analysis(description)
        
        logger.info(f"🤖 智能决策结果: 环境分析={should_analyze_env}, RAG索引={should_build_rag}")
        logger.info(f"🧠 决策理由: {decision_context.get('reasoning', 'N/A')}")

        # Store decision context for later use
        self.decision_context = {
            "should_analyze_env": should_analyze_env,
            "should_build_rag": should_build_rag,
            "decision_context": decision_context,
            "task_context_id": task_context_id
        }

        return self.decision_context

    async def conditional_environment_preparation(self) -> Dict[str, Any]:
        """
        Conditional environment analysis and RAG preparation
        Based on pre-decision analysis results
        """
        should_analyze_env = self.decision_context.get("should_analyze_env", True)
        should_build_rag = self.decision_context.get("should_build_rag", True)

        # 3. Conditional environment analysis
        if should_analyze_env:
            logger.info("🔍 执行环境分析...")
            project_info = await self._analyze_project_structure()
        else:
            logger.info("⏭️ 跳过环境分析，使用现有上下文...")
            # Try to get existing workspace context
            workspace_context = self.workspace_analyzer.get_workspace_context_for_retrieval()
            if workspace_context:
                project_info = workspace_context.get("latest_analysis", {}).get("project_structure", {})
            else:
                # Fallback to basic analysis
                project_info = await self._analyze_project_structure()

        # 4. Conditional RAG retrieval and indexing
        if should_build_rag:
            logger.info("🏗️ 执行RAG索引和检索...")
            # Ensure indexing is complete before retrieval
            await self._ensure_rag_indexing()

        # Store project info for later use
        self.project_info = project_info
        
        return {
            "project_info": project_info,
            "environment_prepared": True,
            "analysis_performed": should_analyze_env,
            "indexing_performed": should_build_rag,
        }

    async def generate_task_plan(self, description: str, relevant_code: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Generate task execution plan (2nd model call)
        Separated from decision analysis for cleaner architecture
        """
        logger.info(f"📋 生成任务执行计划...")

        # Use provided relevant_code or retrieve based on decision context
        if relevant_code is None:
            should_build_rag = self.decision_context.get("should_build_rag", True)
            if should_build_rag:
                relevant_code = await self._retrieve_relevant_code(description)
            else:
                logger.info("⏭️ 跳过RAG检索，尝试使用现有索引...")
                try:
                    relevant_code = await self._retrieve_relevant_code(description)
                except Exception as e:
                    logger.warning(f"现有索引检索失败，使用空上下文: {e}")
                    relevant_code = []

        # Store relevant code contexts
        self.relevant_code_contexts = relevant_code

        # Generate execution plan using LLM
        enhanced_plan = await self._generate_enhanced_plan(
            description, relevant_code, self.project_info
        )

        # Store planning context for later reference
        task_context_id = self.decision_context.get("task_context_id")
        await self.context_manager.add_context(
            content={
                "plan": enhanced_plan,
                "relevant_code": relevant_code,
                "project_info": self.project_info,
                "retriever_type": (
                    "enhanced" if self.use_enhanced_retriever else "basic"
                ),
                "decision_context": self.decision_context,
            },
            context_type=ContextType.PLANNING,
            metadata={"task_id": task_context_id},
            priority=Priority.HIGH,
            tags=["code_plan", "rag_enhanced", "intelligent_decision"],
        )

        # Save analysis results if performed
        should_analyze_env = self.decision_context.get("should_analyze_env", False)
        should_build_rag = self.decision_context.get("should_build_rag", False)
        
        if should_analyze_env or should_build_rag:
            try:
                indexed_files_count = len(relevant_code) if relevant_code else 0
                rag_status = "indexed" if should_build_rag and relevant_code else "partial" if should_build_rag else "none"
                
                self.workspace_analyzer.save_analysis_result(
                    project_structure=self.project_info,
                    environment_info=self.decision_context.get("decision_context", {}).get("workspace_context", {}).get("workspace_status", {}),
                    indexed_files_count=indexed_files_count,
                    rag_status=rag_status
                )
            except Exception as e:
                logger.warning(f"保存分析结果失败: {e}")

        self.tasks = enhanced_plan
        logger.info(f"✅ 任务执行计划生成完成，共{len(enhanced_plan)}个步骤")

        return enhanced_plan

    async def plan_task_with_context(self, description: str) -> List[Dict[str, Any]]:
        """
        Complete task planning with context (combines pre-decision + planning)
        
        Args:
            description: Task description

        Returns:
            LLM-generated task step list focused on core implementation
        """
        logger.info(f"🧠 开始完整任务规划流程: {description[:50]}...")

        # Step 1: Pre-decision analysis (1st model call)
        await self.pre_decision_analysis(description)
        
        # Step 2: Conditional environment preparation
        await self.conditional_environment_preparation()
        
        # Step 3: Generate task plan (2nd model call)
        enhanced_plan = await self.generate_task_plan(description)

        logger.info(
            f"✅ 完整任务规划完成，生成{len(enhanced_plan)}个实现步骤"
        )

        return enhanced_plan

    async def _retrieve_relevant_code(self, description: str) -> List[Dict[str, Any]]:
        """Retrieve code related to the task using enhanced RAG capabilities"""
        if self.use_enhanced_retriever:
            logger.info(
                "🔍 Retrieving relevant code using Enhanced RAG (hybrid search)..."
            )
        else:
            logger.info("🔍 Retrieving relevant code using basic retriever...")

        try:
            # Use enhanced RAG retriever if available
            documents = self.rag_retriever.query_relevant_documents(description)

            relevant_code = []
            for doc in documents:
                code_info = {
                    "file_path": doc.id,
                    "title": doc.title,
                    "url": doc.url,
                    "chunks": [],
                    "retriever_type": (
                        "enhanced" if self.use_enhanced_retriever else "basic"
                    ),
                }

                for chunk in doc.chunks:
                    chunk_info = {
                        "content": chunk.content,
                        "similarity": chunk.similarity,
                    }

                    # Add enhanced retrieval metadata if available
                    if hasattr(chunk, "vector_score"):
                        chunk_info["vector_score"] = getattr(chunk, "vector_score", 0.0)
                    if hasattr(chunk, "keyword_score"):
                        chunk_info["keyword_score"] = getattr(
                            chunk, "keyword_score", 0.0
                        )
                    if hasattr(chunk, "combined_score"):
                        chunk_info["combined_score"] = getattr(
                            chunk, "combined_score", chunk.similarity
                        )

                    code_info["chunks"].append(chunk_info)

                relevant_code.append(code_info)

            retriever_type = "Enhanced RAG" if self.use_enhanced_retriever else "Basic"
            logger.info(
                f"✅ Found {len(relevant_code)} relevant code files using {retriever_type}"
            )
            self.relevant_code_contexts = relevant_code

            return relevant_code

        except Exception as e:
            logger.error(f"❌ Failed to retrieve relevant code: {str(e)}")
            return []

    async def _ensure_rag_indexing(self):
        """确保RAG索引已构建"""
        try:
            if self.use_enhanced_retriever:
                # For enhanced retriever, check if indexing is needed
                stats = self.rag_retriever.get_statistics()
                if stats.get("total_files", 0) == 0:
                    logger.info("🏗️ 构建增强RAG索引...")
                    await self.rag_retriever.build_index_async()
                    stats = self.rag_retriever.get_statistics()
                    self.workspace_analyzer.state_manager.mark_indexing_complete(
                        stats.get("total_files", 0), "indexed"
                    )
            else:
                # For basic retriever, ensure repository is indexed
                stats = self.code_indexer.get_statistics()
                if stats.get("total_files", 0) == 0:
                    logger.info("🏗️ 构建基础代码索引...")
                    index_stats = self.code_indexer.index_repository()
                    self.workspace_analyzer.state_manager.mark_indexing_complete(
                        index_stats.get("indexed_files", 0), "indexed"
                    )
                    
        except Exception as e:
            logger.error(f"RAG索引构建失败: {e}")
            self.workspace_analyzer.state_manager.mark_indexing_complete(0, "partial")

    async def _analyze_project_structure(self) -> Dict[str, Any]:
        """Analyze project structure"""
        logger.info("📊 Analyzing project structure...")

        try:
            # Get indexer statistics
            if self.use_enhanced_retriever:
                # Get enhanced statistics from EnhancedRAGRetriever
                stats = self.rag_retriever.get_statistics()
            else:
                # Get basic statistics from CodeRetriever
                stats = self.code_indexer.get_statistics()

            # Scan repository files
            all_files = self.code_indexer.scan_repository()

            project_info = {
                "total_files": stats.get("total_files", 0),
                "files_by_language": stats.get("files_by_language", {}),
                "total_chunks": stats.get("total_chunks", 0),
                "recent_files": all_files[:20] if all_files else [],
                "main_languages": list(stats.get("files_by_language", {}).keys())[:5],
                "enhanced_indexing": stats.get("enhanced_indexing", False),
                "vector_store_count": stats.get("vector_store_count", 0),
                "hybrid_search_enabled": stats.get("hybrid_search_enabled", False),
            }

            self.project_info = project_info
            logger.info(
                f"✅ Project analysis completed: {project_info['total_files']} files, Enhanced: {project_info.get('enhanced_indexing', False)}"
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
        """Generate enhanced execution plan using LLM"""
        logger.info("⚡ Generating enhanced execution plan using LLM...")

        try:
            # Prepare context for template
            template_context = {
                "task_description": description,
                "relevant_files": [code["file_path"] for code in relevant_code][
                    :5
                ],  # Only top 5 files
                "relevant_files_count": len(relevant_code),
                "project_languages": project_info.get("main_languages", [])[
                    :3
                ],  # Only top 3 languages
                "total_files": project_info.get("total_files", 0),
                "has_similar_code": len(relevant_code) > 0,
                "retriever_type": (
                    "enhanced" if self.use_enhanced_retriever else "basic"
                ),
            }

            # Get LLM to generate plan using template
            llm = get_llm_by_type("reasoning")

            # Load prompt template
            from src.prompts.template import get_prompt_template, env

            template = env.get_template("rag_task_planner.md")
            plan_prompt = template.render(**template_context)

            response = await llm.ainvoke(plan_prompt)

            # Parse LLM response and create plan
            try:
                import json
                import re

                # Extract JSON from response
                json_match = re.search(r"\[.*\]", response.content, re.DOTALL)
                if json_match:
                    plan_data = json.loads(json_match.group(0))
                else:
                    # Fallback: create simple plan
                    plan_data = [
                        {
                            "id": 1,
                            "title": "Execute Task",
                            "description": description,
                            "type": "implementation",
                            "priority": 1,
                            "tools": ["all_available"],
                        }
                    ]

                # Enhance plan with context info
                for step in plan_data:
                    step["rag_enhanced"] = True
                    step["context_available"] = template_context["has_similar_code"]

                logger.info(f"✅ Generated {len(plan_data)} execution steps")
                return plan_data

            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"Failed to parse LLM plan response: {e}")
                # Return simple fallback plan
                return [
                    {
                        "id": 1,
                        "title": "Execute Task",
                        "description": description,
                        "type": "implementation",
                        "priority": 1,
                        "tools": ["all_available"],
                        "rag_enhanced": True,
                        "context_available": template_context["has_similar_code"],
                    }
                ]

        except Exception as e:
            logger.error(f"❌ Plan generation failed: {str(e)}")
            # Return minimal plan on error
            return [
                {
                    "id": 1,
                    "title": "Execute Task",
                    "description": description,
                    "type": "implementation",
                    "priority": 1,
                    "tools": ["all_available"],
                    "rag_enhanced": True,
                    "context_available": len(relevant_code) > 0,
                }
            ]

    async def get_context_for_step(self, step_id: int) -> Dict[str, Any]:
        """Get essential context for a specific step - simplified for efficiency"""
        if step_id >= len(self.tasks):
            return {}

        step = self.tasks[step_id]

        # Only pass essential context - top 3 most relevant files
        relevant_files = []
        for code_info in self.relevant_code_contexts[:3]:
            # Extract only essential info
            file_info = {
                "file_path": code_info["file_path"],
                "has_high_similarity": any(
                    chunk.get("similarity", 0) > 0.6
                    for chunk in code_info.get("chunks", [])
                ),
            }
            relevant_files.append(file_info)

        return {
            "step_info": {
                "title": step.get("title", ""),
                "type": step.get("type", ""),
                "description": step.get("description", ""),
            },
            "relevant_files": relevant_files,
            "project_languages": self.project_info.get("main_languages", [])[
                :2
            ],  # Only top 2
            "has_similar_code": len(self.relevant_code_contexts) > 0,
        }
