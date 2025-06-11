
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from langgraph.prebuilt import create_react_agent
from src.agents.rag_code_agent.task_planner import RAGEnhancedCodeTaskPlanner
from src.llms.llm import get_llm_by_type
from src.prompts import apply_prompt_template


from src.context.manager import ContextManager
from src.context.base import ContextType, Priority

logger = logging.getLogger(__name__)

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
        """Enhanced task execution with pre-decision analysis and re-planning support"""
        logger.info("🚀 开始RAG增强任务执行")

        try:
            # Step 1: Pre-decision analysis (1st model call)
            logger.info("🧠 执行预先决策分析...")
            await self.task_planner.pre_decision_analysis(task_description)
            
            # Step 2: Conditional environment preparation
            logger.info("📊 准备执行环境...")
            await self.task_planner.conditional_environment_preparation()
            
            # Step 3: Generate initial task plan (2nd model call)
            logger.info("📋 生成初始任务计划...")
            plan = await self.task_planner.generate_task_plan(task_description)

            if not plan:
                return {
                    "success": False,
                    "error": "RAG enhanced task planning failed",
                    "results": [],
                }

            # Step 4: Enhanced execution loop with re-planning support
            results = []
            generated_scripts = []  # Track generated scripts for cleanup
            
            for i, step in enumerate(plan):
                logger.info(f"📋 执行步骤 {i+1}/{len(plan)}: {step['title']}")

                # Enhanced step execution with environment awareness
                step_result, need_replanning, script_files = await self._execute_enhanced_step(
                    step, task_description, i, len(plan)
                )

                # Track generated scripts
                generated_scripts.extend(script_files)

                # Check if step requests re-planning
                if need_replanning:
                    logger.info(f"🔄 步骤 {i+1} 请求重新规划")
                    
                    # Re-plan remaining tasks
                    remaining_description = step_result.get("replanning_request", task_description)
                    new_plan = await self.task_planner.generate_task_plan(remaining_description)
                    
                    if new_plan:
                        logger.info(f"📋 重新规划完成，新增 {len(new_plan)} 个步骤")
                        # Insert new steps after current step
                        plan = plan[:i+1] + new_plan + plan[i+1:]
                    
                    # Mark current step as planning step
                    step_result["replanning_performed"] = True

                results.append(step_result)

                if step_result.get("success"):
                    logger.info(f"✅ 步骤 {i+1} 执行成功")
                else:
                    logger.warning(f"⚠️ 步骤 {i+1} 执行失败: {step_result.get('error', 'Unknown error')}")

            # Step 5: Cleanup generated scripts
            await self._cleanup_generated_scripts(generated_scripts)

            # Step 6: Generate final result
            success_count = sum(1 for r in results if r.get("success", False))
            overall_success = success_count == len(results)

            final_result = {
                "success": overall_success,
                "total_steps": len(plan),
                "successful_steps": success_count,
                "results": results,
                "rag_enhanced": True,
                "context_used": True,
                "scripts_generated": len(generated_scripts),
                "scripts_cleaned": True,
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
                f"🎉 RAG增强任务执行完成: {success_count}/{len(plan)} 步骤成功"
            )

            return final_result

        except Exception as e:
            logger.error(f"❌ RAG增强任务执行失败: {str(e)}")
            return {"success": False, "error": str(e), "rag_enhanced": True}

    async def _execute_enhanced_step(
        self, step: Dict[str, Any], original_task: str, step_index: int, total_steps: int
    ) -> tuple[Dict[str, Any], bool, List[str]]:
        """
        Enhanced step execution with environment info, script guidance, and re-planning detection
        
        Returns:
            (step_result, need_replanning, generated_script_files)
        """
        
        # Get step context with enhanced environment information
        step_context = await self.task_planner.get_context_for_step(step_index)
        
        # Build enhanced step prompt with environment awareness
        enhanced_prompt = self._build_enhanced_step_prompt(
            step, step_context, original_task, step_index, total_steps
        )

        # Build agent input state
        agent_state = {
            "messages": [
                {
                    "role": "user",
                    "content": enhanced_prompt,
                }
            ],
            "rag_context": step_context,
            "current_step": step,
            "step_index": step_index,
            "environment_info": self._get_current_environment_summary(),
        }

        generated_scripts = []
        need_replanning = False

        try:
            # Execute agent step
            step_result = await self.agent.ainvoke(agent_state)

            # Parse result for replanning requests and script files
            result_content = step_result.content if hasattr(step_result, 'content') else str(step_result)
            
            # Check for replanning request
            if "NEED_REPLANNING" in result_content or "需要重新规划" in result_content:
                need_replanning = True
                logger.info(f"步骤 {step_index+1} 请求重新规划")

            # Extract script file references for tracking
            import re
            script_patterns = [
                r'create.*?script.*?([a-zA-Z0-9_./]+\.(?:py|sh|js|ts))',
                r'生成.*?脚本.*?([a-zA-Z0-9_./]+\.(?:py|sh|js|ts))',
                r'([a-zA-Z0-9_./]+\.(?:py|sh|js|ts)).*?(?:script|脚本)',
            ]
            
            for pattern in script_patterns:
                matches = re.findall(pattern, result_content, re.IGNORECASE)
                generated_scripts.extend(matches)

            # Process result
            result = {
                "step_id": step_index,
                "step_title": step.get("title", "Execute Task"),
                "success": True,
                "result": step_result,
                "rag_enhanced": True,
                "environment_aware": True,
                "script_guidance_enabled": True,
            }

            if need_replanning:
                # Extract replanning request details
                replanning_match = re.search(
                    r'(?:NEED_REPLANNING|需要重新规划)[:：]?\s*(.+)', 
                    result_content, 
                    re.IGNORECASE | re.DOTALL
                )
                if replanning_match:
                    result["replanning_request"] = replanning_match.group(1).strip()
                else:
                    result["replanning_request"] = original_task

            # Add result to context manager
            await self.context_manager.add_context(
                content=result,
                context_type=ContextType.EXECUTION_RESULT,
                metadata={"step_id": step_index, "task_type": "code_task"},
                priority=Priority.MEDIUM,
                tags=["execution_result", "rag_enhanced", "environment_aware"],
            )

            return result, need_replanning, generated_scripts

        except Exception as e:
            logger.error(f"❌ 步骤 {step_index+1} 执行失败: {str(e)}")
            
            error_result = {
                "step_id": step_index,
                "step_title": step.get("title", "Execute Task"),
                "success": False,
                "error": str(e),
                "rag_enhanced": True,
                "environment_aware": True,
            }
            
            return error_result, False, generated_scripts

    def _build_enhanced_step_prompt(
        self, step: Dict[str, Any], step_context: Dict[str, Any], 
        original_task: str, step_index: int, total_steps: int
    ) -> str:
        """Build enhanced step prompt with environment information and script guidance"""

        # Get current environment summary
        env_summary = self._get_current_environment_summary()
        
        # Prepare enhanced context for template
        template_context = {
            "step_title": step.get("title", "Execute Task"),
            "original_task": original_task,
            "step_description": step.get("description", "Execute the task"),
            "step_number": step_index + 1,
            "total_steps": total_steps,
            "relevant_files": step_context.get("relevant_files", [])[:5],  # Limit to top 5
            "project_languages": step_context.get("project_languages", [])[:3],  # Top 3 languages
            "environment_summary": env_summary,
            "available_tools": self._get_available_tools_summary(),
            "script_guidance": True,
            "can_request_replanning": True,
        }

        # Load and render enhanced template
        from src.prompts.template import env

        template = env.get_template("enhanced_step_execution.md")
        return template.render(**template_context)

    def _get_current_environment_summary(self) -> Dict[str, Any]:
        """Get current environment summary for step execution"""
        
        project_info = self.task_planner.project_info
        
        return {
            "repo_path": str(self.task_planner.repo_path),
            "total_files": project_info.get("total_files", 0),
            "main_languages": project_info.get("main_languages", [])[:3],
            "recent_files": project_info.get("recent_files", [])[:10],
            "enhanced_rag_enabled": self.use_enhanced_retriever,
            "context_available": len(self.task_planner.relevant_code_contexts) > 0,
            "indexed_files": len(self.task_planner.relevant_code_contexts),
        }

    def _get_available_tools_summary(self) -> List[str]:
        """Get summary of available tools for the agent"""
        
        tool_names = []
        for tool in self.tools:
            if hasattr(tool, 'name'):
                tool_names.append(tool.name)
            elif hasattr(tool, '__name__'):
                tool_names.append(tool.__name__)
            else:
                tool_names.append(str(tool))
        
        return tool_names[:10]  # Limit to top 10 tools

    async def _cleanup_generated_scripts(self, script_files: List[str]) -> None:
        """Clean up generated script files after task completion"""
        
        if not script_files:
            logger.info("🗑️ 无生成的脚本文件需要清理")
            return
            
        logger.info(f"🗑️ 清理 {len(script_files)} 个生成的脚本文件...")
        
        cleaned_count = 0
        for script_file in script_files:
            try:
                script_path = Path(script_file)
                if script_path.exists() and script_path.is_file():
                    # Check if it's likely a temporary script
                    if any(keyword in script_file.lower() for keyword in ['temp', 'tmp', 'script', 'auto_generated']):
                        script_path.unlink()
                        cleaned_count += 1
                        logger.debug(f"🗑️ 已删除脚本文件: {script_file}")
                    else:
                        logger.debug(f"⚠️ 跳过删除非临时脚本: {script_file}")
                        
            except Exception as e:
                logger.warning(f"⚠️ 删除脚本文件失败 {script_file}: {e}")
        
        logger.info(f"✅ 已清理 {cleaned_count}/{len(script_files)} 个脚本文件")

    def _build_step_prompt(
        self, step: Dict[str, Any], step_context: Dict[str, Any], original_task: str
    ) -> str:
        """Build simplified prompt for a specific step using template (legacy method)"""

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

