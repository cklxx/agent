#!/usr/bin/env python3
"""
Enhanced RAG Integration Demo

This script demonstrates the integration of EnhancedRAGRetriever
into the RAG-Enhanced Code Agent, showcasing hybrid search capabilities.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.agents.rag_enhanced_code_agent import (
    create_rag_enhanced_code_agent,
    run_rag_enhanced_code_agent,
)

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_embedding_config():
    """Get embedding configuration from environment or use defaults"""
    return {
        "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        "model": os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
        "api_key": os.getenv("OPENAI_API_KEY", "your-api-key-here"),
        "dimensions": int(os.getenv("EMBEDDING_DIMENSIONS", "1536")),
    }


async def demo_basic_vs_enhanced_retrieval():
    """Demonstrate the difference between basic and enhanced retrieval"""
    repo_path = "."  # Current repository
    test_query = "Python function for file operations"

    logger.info("🚀 Starting Enhanced RAG Integration Demo")
    logger.info(f"Repository: {repo_path}")
    logger.info(f"Test Query: {test_query}")

    # Test with basic retriever
    logger.info("\n" + "=" * 50)
    logger.info("🔍 Testing with Basic Retriever")
    logger.info("=" * 50)

    try:
        basic_agent = create_rag_enhanced_code_agent(
            repo_path=repo_path, use_enhanced_retriever=False  # 保留此处用于演示对比
        )

        # Get basic retrieval results
        basic_plan = await basic_agent.task_planner.plan_task_with_context(test_query)
        basic_relevant_code = basic_agent.task_planner.relevant_code_contexts

        logger.info(f"✅ Basic Retriever Results:")
        logger.info(f"   - Found {len(basic_relevant_code)} relevant files")
        logger.info(f"   - Generated {len(basic_plan)} planning steps")

        for i, code_info in enumerate(basic_relevant_code[:3]):
            logger.info(f"   - File {i+1}: {code_info['file_path']}")
            logger.info(f"     Chunks: {len(code_info.get('chunks', []))}")

    except Exception as e:
        logger.error(f"❌ Basic retriever test failed: {e}")

    # Test with enhanced retriever
    logger.info("\n" + "=" * 50)
    logger.info("🚀 Testing with Enhanced RAG Retriever")
    logger.info("=" * 50)

    try:
        embedding_config = get_embedding_config()
        logger.info(f"Using embedding model: {embedding_config['model']}")

        enhanced_agent = create_rag_enhanced_code_agent(
            repo_path=repo_path,
            use_enhanced_retriever=True,
            embedding_config=embedding_config,
        )

        # Get enhanced retrieval results
        enhanced_plan = await enhanced_agent.task_planner.plan_task_with_context(
            test_query
        )
        enhanced_relevant_code = enhanced_agent.task_planner.relevant_code_contexts
        enhanced_stats = enhanced_agent.task_planner.rag_retriever.get_statistics()

        logger.info(f"✅ Enhanced RAG Retriever Results:")
        logger.info(f"   - Found {len(enhanced_relevant_code)} relevant files")
        logger.info(f"   - Generated {len(enhanced_plan)} planning steps")
        logger.info(
            f"   - Vector Store Entries: {enhanced_stats.get('vector_store_count', 0)}"
        )
        logger.info(
            f"   - Hybrid Search Enabled: {enhanced_stats.get('hybrid_search_enabled', False)}"
        )

        for i, code_info in enumerate(enhanced_relevant_code[:3]):
            logger.info(f"   - File {i+1}: {code_info['file_path']}")
            logger.info(
                f"     Retriever Type: {code_info.get('retriever_type', 'unknown')}"
            )
            logger.info(f"     Chunks: {len(code_info.get('chunks', []))}")

            # Show enhanced scoring if available
            chunks = code_info.get("chunks", [])
            if chunks and "combined_score" in chunks[0]:
                best_chunk = max(chunks, key=lambda x: x.get("combined_score", 0))
                logger.info(f"     Best Match Scores:")
                logger.info(
                    f"       - Combined: {best_chunk.get('combined_score', 0):.3f}"
                )
                logger.info(f"       - Vector: {best_chunk.get('vector_score', 0):.3f}")
                logger.info(
                    f"       - Keyword: {best_chunk.get('keyword_score', 0):.3f}"
                )

    except Exception as e:
        logger.error(f"❌ Enhanced retriever test failed: {e}")


async def demo_full_task_execution():
    """Demonstrate full task execution with enhanced retrieval"""
    logger.info("\n" + "=" * 50)
    logger.info("🎯 Demonstrating Full Task Execution")
    logger.info("=" * 50)

    task_description = (
        "Analyze the codebase and suggest improvements for the RAG retrieval system"
    )

    try:
        embedding_config = get_embedding_config()

        # Run with enhanced retrieval
        result = await run_rag_enhanced_code_agent(
            task_description=task_description,
            repo_path=".",
            use_enhanced_retriever=True,
            embedding_config=embedding_config,
            max_iterations=3,
        )

        logger.info(f"✅ Task Execution Results:")
        logger.info(f"   - Success: {result.get('success', False)}")
        logger.info(f"   - Total Steps: {result.get('total_steps', 0)}")
        logger.info(f"   - Successful Steps: {result.get('successful_steps', 0)}")
        logger.info(
            f"   - Retrieval Method: {result.get('retrieval_method', 'unknown')}"
        )
        logger.info(f"   - RAG Enhanced: {result.get('rag_enhanced', False)}")
        logger.info(
            f"   - Relevant Files Analyzed: {result.get('relevant_files_analyzed', 0)}"
        )

        if result.get("success"):
            logger.info("🎉 Task completed successfully with Enhanced RAG!")
        else:
            logger.warning("⚠️ Task completed with some issues")

    except Exception as e:
        logger.error(f"❌ Full task execution failed: {e}")


async def main():
    """Main demo function"""
    logger.info("Enhanced RAG Integration Demo Starting...")

    # Check if API key is set
    if (
        not os.getenv("OPENAI_API_KEY")
        or os.getenv("OPENAI_API_KEY") == "your-api-key-here"
    ):
        logger.warning("⚠️ OPENAI_API_KEY not set - using fallback configuration")
        logger.warning("   For full functionality, set your OpenAI API key")

    try:
        # Demo 1: Compare basic vs enhanced retrieval
        await demo_basic_vs_enhanced_retrieval()

        # Demo 2: Full task execution
        await demo_full_task_execution()

        logger.info("\n🎉 Enhanced RAG Integration Demo completed!")
        logger.info("Key Benefits Demonstrated:")
        logger.info("  ✅ Hybrid search combining vector and keyword matching")
        logger.info("  ✅ Enhanced scoring for better relevance ranking")
        logger.info("  ✅ Seamless fallback to basic retriever if needed")
        logger.info("  ✅ Full integration with RAG-Enhanced Code Agent")

    except KeyboardInterrupt:
        logger.info("Demo interrupted by user")
    except Exception as e:
        logger.error(f"Demo failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
