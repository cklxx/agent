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

from src.agents.rag_code_agent.agent import RAGEnhancedCodeAgent

logger = logging.getLogger(__name__)

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
