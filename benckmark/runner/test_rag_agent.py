#!/usr/bin/env python3
"""
RAG Code Agent 专用测试脚本
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.rag_enhanced_code_agent_workflow import RAGEnhancedCodeAgentWorkflow


async def test_rag_agent(workspace_path: str = None):
    """测试RAG Code Agent功能"""
    if workspace_path is None:
        workspace_path = str(project_root)

    print(f"🚀 开始测试RAG Code Agent")
    print(f"📁 工作区路径: {workspace_path}")

    try:
        # 初始化RAG增强代码代理
        workflow = RAGEnhancedCodeAgentWorkflow(repo_path=workspace_path)

        # 测试1: 代码库分析
        print("\n🔍 测试1: 代码库分析")
        analysis_result = await workflow.analyze_codebase()
        print(
            f"   ✅ 分析完成: {analysis_result.get('project_structure', {}).get('total_files', 0)} 个文件"
        )

        # 测试2: 简单代码任务
        print("\n💻 测试2: 代码生成任务")
        task_result = await workflow.execute_task(
            "请分析当前项目的主要功能模块，并生成一个简单的项目概览文档",
            max_iterations=3,
        )
        print(f"   ✅ 任务完成: {'成功' if task_result.get('success') else '失败'}")

        # 测试3: 改进建议
        print("\n💡 测试3: 代码改进建议")
        improvement_result = await workflow.suggest_improvements("代码质量和结构优化")
        print(
            f"   ✅ 建议生成: {'成功' if improvement_result.get('success') else '失败'}"
        )

        print("\n🎉 RAG Code Agent 测试完成!")
        return True

    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        return False


if __name__ == "__main__":
    workspace = sys.argv[1] if len(sys.argv) > 1 else None
    result = asyncio.run(test_rag_agent(workspace))
    sys.exit(0 if result else 1)
