# SPDX-License-Identifier: MIT

"""
RAG-Enhanced Code Agent - Integrates context management and code retrieval capabilities

Optimizations made:
- Simplified context passing - only essential information transmitted to models
- LLM-generated execution plans instead of predefined templates
- RAG and environment analysis handled automatically (not included in plans)
- Verification steps determined by model as needed
- Streamlined prompts for better efficiency
- All prompts now use apply_prompt_template for consistent template management
"""

import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from langgraph.prebuilt import create_react_agent
from src.llms.llm import get_llm_by_type
from src.prompts import apply_prompt_template

# Enhanced RAG components
from src.rag.enhanced_retriever import EnhancedRAGRetriever
from src.rag.code_retriever import CodeRetriever

# Context components
from src.context.manager import ContextManager
from src.context.base import ContextType, Priority

logger = logging.getLogger(__name__)


class RAGEnhancedCodeTaskPlanner:
    """Enhanced code task planner that integrates RAG and Context functionality"""

    def __init__(
        self,
        repo_path: str = ".",
        context_manager: Optional[ContextManager] = None,
        use_enhanced_retriever: bool = True,
        embedding_config: Optional[Dict[str, Any]] = None,
    ):
        self.repo_path = repo_path
        self.context_manager = context_manager or ContextManager()
        self.use_enhanced_retriever = use_enhanced_retriever

        # Initialize RAG components with enhanced retriever
        if use_enhanced_retriever:
            try:
                logger.info(
                    "Initializing Enhanced RAG Retriever with hybrid search capabilities"
                )
                self.rag_retriever = EnhancedRAGRetriever(
                    repo_path=repo_path,
                    db_path=f"temp/rag_data/enhanced_{Path(repo_path).name}",
                    embedding_config=embedding_config,
                )
                self.code_indexer = self.rag_retriever.base_retriever.indexer
                logger.info("✅ Enhanced RAG Retriever initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize Enhanced RAG Retriever: {e}")
                logger.info("Falling back to basic CodeRetriever")
                self.rag_retriever = CodeRetriever(repo_path)
                self.code_indexer = self.rag_retriever.indexer
                self.use_enhanced_retriever = False
        else:
            # Use basic code retriever as fallback
            logger.info("Using basic CodeRetriever")
            self.rag_retriever = CodeRetriever(repo_path)
            self.code_indexer = self.rag_retriever.indexer

        self.tasks = []
        self.current_step = 0

        # Store relevant context information
        self.relevant_code_contexts: List[Dict[str, Any]] = []
        self.project_structure: Dict[str, Any] = {}

        logger.info(
            f"RAG-enhanced task planner initialized - Enhanced: {self.use_enhanced_retriever}"
        )

    async def plan_task_with_context(self, description: str) -> List[Dict[str, Any]]:
        """
        Plan tasks based on RAG and Context information

        Note: RAG context analysis and environment assessment are performed automatically
        and do not appear as explicit steps in the generated plan.

        Args:
            description: Task description

        Returns:
            LLM-generated task step list focused on core implementation
        """
        logger.info(f"🧠 Starting RAG-based task planning: {description[:50]}...")

        # 1. Add task to context manager
        task_context_id = await self.context_manager.add_context(
            content=description,
            context_type=ContextType.TASK,
            metadata={
                "task_type": "code_task",
                "status": "planning",
                "enhanced_rag": self.use_enhanced_retriever,
            },
            priority=Priority.HIGH,
            tags=["code_task", "planning"],
        )

        # 2. Automatic RAG retrieval (not shown in plan steps)
        relevant_code = await self._retrieve_relevant_code(description)

        # 3. Automatic environment analysis (not shown in plan steps)
        project_info = await self._analyze_project_structure()

        # 4. LLM generates core implementation plan only
        enhanced_plan = await self._generate_enhanced_plan(
            description, relevant_code, project_info
        )

        # 5. Store planning context for later reference
        await self.context_manager.add_context(
            content={
                "plan": enhanced_plan,
                "relevant_code": relevant_code,
                "project_info": project_info,
                "retriever_type": (
                    "enhanced" if self.use_enhanced_retriever else "basic"
                ),
            },
            context_type=ContextType.PLANNING,
            metadata={"task_id": task_context_id},
            priority=Priority.HIGH,
            tags=["code_plan", "rag_enhanced"],
        )

        self.tasks = enhanced_plan
        logger.info(
            f"✅ RAG-enhanced planning completed, generated {len(enhanced_plan)} implementation steps"
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

            self.project_structure = project_info
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
            "project_languages": self.project_structure.get("main_languages", [])[
                :2
            ],  # Only top 2
            "has_similar_code": len(self.relevant_code_contexts) > 0,
        }


class RAGEnhancedCodeAgent:
    """RAG enhanced code agent with hybrid retrieval capabilities"""

    def __init__(
        self,
        repo_path: str = ".",
        tools: Optional[List[Any]] = None,
        use_enhanced_retriever: bool = True,
        embedding_config: Optional[Dict[str, Any]] = None,
    ):
        self.repo_path = repo_path
        self.tools = tools or []
        self.use_enhanced_retriever = use_enhanced_retriever

        # Initialize enhanced components
        self.context_manager = ContextManager()
        self.task_planner = RAGEnhancedCodeTaskPlanner(
            repo_path,
            self.context_manager,
            use_enhanced_retriever=use_enhanced_retriever,
            embedding_config=embedding_config,
        )

        # Create base agent
        self.agent = self._create_agent()

        retriever_type = "Enhanced RAG" if use_enhanced_retriever else "Basic"
        logger.info(
            f"RAG Enhanced Code Agent initialization completed - Using: {retriever_type}"
        )

    def _create_agent(self):
        """Create RAG enhanced agent"""
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
        """Apply RAG enhanced prompt template"""

        # Get RAG context information
        rag_context = state.get("rag_context", {})
        relevant_code = rag_context.get("relevant_code", [])
        project_info = rag_context.get("project_structure", {})

        # Build enhanced state information
        enhanced_state = {
            **state,
            "rag_context_available": len(relevant_code) > 0,
            "relevant_files_count": len(relevant_code),
            "project_languages": project_info.get("main_languages", []),
            "has_context_manager": True,
            "enhanced_rag_enabled": self.use_enhanced_retriever,
            "hybrid_search_enabled": project_info.get("hybrid_search_enabled", False),
            "vector_store_count": project_info.get("vector_store_count", 0),
        }

        # Use RAG enhanced prompt template
        base_messages = apply_prompt_template("rag_enhanced_code_agent", enhanced_state)

        # Add RAG specific system prompt
        if relevant_code:
            rag_prompt = self._build_rag_context_prompt(relevant_code, project_info)
            base_messages.insert(1, {"role": "system", "content": rag_prompt})

        return base_messages

    def _build_rag_context_prompt(
        self, relevant_code: List[Dict[str, Any]], project_info: Dict[str, Any]
    ) -> str:
        """Build simplified RAG context prompt using template"""

        # Prepare context for template
        template_context = {
            "relevant_code": [],
            "project_languages": project_info.get("main_languages", []),
        }

        # Process relevant code for template
        for code_info in relevant_code[:3]:
            file_path = code_info["file_path"]
            chunks = code_info.get("chunks", [])

            # Find best chunk
            best_chunk = None
            if chunks:
                high_similarity = [c for c in chunks if c.get("similarity", 0) > 0.6]
                if high_similarity:
                    best_chunk = max(
                        high_similarity, key=lambda x: x.get("similarity", 0)
                    )

            template_context["relevant_code"].append(
                {"file_path": file_path, "best_chunk": best_chunk}
            )

        # Load and render template
        from src.prompts.template import env

        template = env.get_template("rag_context.md")
        return template.render(**template_context)

    async def execute_task_with_rag(
        self, task_description: str, max_iterations: int = 5
    ) -> Dict[str, Any]:
        """Use RAG enhanced to execute task"""
        logger.info("🚀 Starting RAG Enhanced task execution")

        try:
            # 1. Use RAG for task planning
            plan = await self.task_planner.plan_task_with_context(task_description)

            if not plan:
                return {
                    "success": False,
                    "error": "RAG enhanced task planning failed",
                    "results": [],
                }

            # 2. Execute task steps
            results = []
            for i, step in enumerate(plan):
                logger.info(f"📋 Executing step {i+1}/{len(plan)}: {step['title']}")

                # Get step related context
                step_context = await self.task_planner.get_context_for_step(i)

                # Build agent input state
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

                # Execute agent step
                try:
                    step_result = await self.agent.ainvoke(agent_state)

                    # Process result
                    result = {
                        "step_id": i,
                        "step_title": step["title"],
                        "success": True,
                        "result": step_result,
                        "rag_enhanced": True,
                    }

                    # Add result to context manager
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

            # 3. Generate final result
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

            # Add final result to context
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
        """Build simplified prompt for a specific step using template"""

        # Prepare context for template
        template_context = {
            "step_title": step.get("title", "Execute Task"),
            "original_task": original_task,
            "step_description": step.get("description", "Execute the task"),
            "relevant_files": step_context.get("relevant_files", []),
            "project_languages": step_context.get("project_languages", []),
        }

        # Load and render template
        from src.prompts.template import env

        template = env.get_template("rag_step_execution.md")
        return template.render(**template_context)


# Factory function
def create_rag_enhanced_code_agent(
    repo_path: str = ".",
    tools: Optional[List[Any]] = None,
    use_enhanced_retriever: bool = True,
    embedding_config: Optional[Dict[str, Any]] = None,
) -> RAGEnhancedCodeAgent:
    """
    Create RAG enhanced code agent with optional hybrid retrieval

    Args:
        repo_path: Working code path
        tools: Available tools list
        use_enhanced_retriever: Whether to use Enhanced RAG Retriever with hybrid search
        embedding_config: Configuration for embedding service (for enhanced retriever)

    Returns:
        RAG enhanced code agent instance
    """
    retriever_type = "Enhanced RAG" if use_enhanced_retriever else "Basic"
    logger.info(
        f"Creating RAG Enhanced Code Agent - repository path: {repo_path}, Retriever: {retriever_type}"
    )

    try:
        agent = RAGEnhancedCodeAgent(
            repo_path=repo_path,
            tools=tools,
            use_enhanced_retriever=use_enhanced_retriever,
            embedding_config=embedding_config,
        )
        logger.info(
            f"✅ RAG Enhanced Code Agent created successfully with {retriever_type}"
        )
        return agent
    except Exception as e:
        logger.error(f"❌ Failed to create RAG Enhanced Code Agent: {str(e)}")
        if use_enhanced_retriever:
            logger.info("🔄 Retrying with basic retriever as fallback...")
            return RAGEnhancedCodeAgent(
                repo_path=repo_path, tools=tools, use_enhanced_retriever=False
            )
        else:
            raise


# Asynchronous run function
async def run_rag_enhanced_code_agent(
    task_description: str,
    repo_path: str = ".",
    tools: Optional[List[Any]] = None,
    max_iterations: int = 5,
    use_enhanced_retriever: bool = True,
    embedding_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Run RAG enhanced code agent task with hybrid retrieval capabilities

    Args:
        task_description: Task description
        repo_path: Code repository path
        tools: Available tools list
        max_iterations: Maximum iteration count
        use_enhanced_retriever: Whether to use Enhanced RAG Retriever
        embedding_config: Configuration for embedding service

    Returns:
        Task execution result with enhanced retrieval information
    """
    agent = create_rag_enhanced_code_agent(
        repo_path=repo_path,
        tools=tools,
        use_enhanced_retriever=use_enhanced_retriever,
        embedding_config=embedding_config,
    )

    result = await agent.execute_task_with_rag(task_description, max_iterations)

    # Add retrieval method information to result
    result["retrieval_method"] = "enhanced" if agent.use_enhanced_retriever else "basic"

    return result
