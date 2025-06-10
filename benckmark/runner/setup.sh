#!/bin/bash

# AI Agent Benchmark 测试环境快速设置脚本

set -e

echo "============================================"
echo "  AI Agent Benchmark 测试环境设置"
echo "============================================"

# 获取项目根目录路径
PROJECT_ROOT=$(cd ../.. && pwd)
echo "项目根目录: $PROJECT_ROOT"

# 检查Python版本
echo "检查Python环境..."
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到Python3，请先安装Python 3.12或更高版本"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "发现Python版本: $PYTHON_VERSION"

# 检查是否在temp/benchmark目录
CURRENT_DIR=$(basename "$PWD")
if [ "$CURRENT_DIR" != "runner" ]; then
    echo "错误: 请在benchmark/runner目录下运行此脚本"
    exit 1
fi

# 使用项目的uv环境（如果存在）
if [ -f "$PROJECT_ROOT/pyproject.toml" ]; then
    echo "检测到uv项目，使用项目环境..."
    cd "$PROJECT_ROOT"
    if command -v uv &> /dev/null; then
        echo "使用uv安装依赖..."
        uv sync
        UV_PYTHON=$(uv run which python)
        echo "uv Python路径: $UV_PYTHON"
        cd - > /dev/null
    else
        echo "警告: 未找到uv命令，尝试使用传统虚拟环境..."
        cd - > /dev/null
    fi
else
    # 创建虚拟环境（备用方案）
    if [ ! -d "venv" ]; then
        echo "创建Python虚拟环境..."
        python3 -m venv venv
    fi

    echo "激活虚拟环境..."
    source venv/bin/activate

    # 升级pip
    echo "升级pip..."
    pip install --upgrade pip
fi

# 安装benchmark依赖
echo "安装benchmark依赖包..."
if [ -f "requirements.txt" ]; then
    if command -v uv &> /dev/null; then
        cd "$PROJECT_ROOT"
        uv add $(grep -v '^#' benckmark/runner/requirements.txt | tr '\n' ' ')
        cd - > /dev/null
    else
        pip install -r requirements.txt
    fi
else
    echo "警告: requirements.txt 文件不存在，手动安装基础依赖..."
    if command -v uv &> /dev/null; then
        cd "$PROJECT_ROOT"
        uv add PyYAML pytest asyncio psutil
        cd - > /dev/null
    else
        pip install PyYAML pytest asyncio psutil
    fi
fi

# 创建必要的目录
echo "创建必要的目录结构..."
mkdir -p logs
mkdir -p sandbox
mkdir -p reports
mkdir -p test_data

# 创建工作区配置文件
echo "创建工作区配置..."
cat > config/workspace_config.yaml << EOF
# 工作区配置
workspace:
  root_path: "$PROJECT_ROOT"
  temp_path: "$PROJECT_ROOT/temp"
  rag_data_path: "$PROJECT_ROOT/temp/rag_data"
  context_db_path: "$PROJECT_ROOT/temp/contexts.db"
  benchmark_path: "$PROJECT_ROOT/benckmark"

# RAG Code Agent 测试配置
rag_agent:
  enabled: true
  test_scenarios:
    - name: "代码理解与分析"
      description: "测试RAG Agent对现有代码的理解能力"
    - name: "代码生成与改进"
      description: "测试基于RAG的代码生成能力"
    - name: "项目结构分析"
      description: "测试对整个项目结构的分析能力"
    - name: "智能重构建议"
      description: "测试基于历史代码模式的重构建议"

# 测试环境配置
environment:
  use_project_env: true
  python_path: "$(which python)"
  working_directory: "$PROJECT_ROOT"
EOF

# 创建RAG Agent测试脚本
echo "创建RAG Agent测试脚本..."
cat > test_rag_agent.py << 'EOF'
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
        print(f"   ✅ 分析完成: {analysis_result.get('project_structure', {}).get('total_files', 0)} 个文件")
        
        # 测试2: 简单代码任务
        print("\n💻 测试2: 代码生成任务")
        task_result = await workflow.execute_task(
            "请分析当前项目的主要功能模块，并生成一个简单的项目概览文档",
            max_iterations=3
        )
        print(f"   ✅ 任务完成: {'成功' if task_result.get('success') else '失败'}")
        
        # 测试3: 改进建议
        print("\n💡 测试3: 代码改进建议")
        improvement_result = await workflow.suggest_improvements("代码质量和结构优化")
        print(f"   ✅ 建议生成: {'成功' if improvement_result.get('success') else '失败'}")
        
        print("\n🎉 RAG Code Agent 测试完成!")
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        return False

if __name__ == "__main__":
    workspace = sys.argv[1] if len(sys.argv) > 1 else None
    result = asyncio.run(test_rag_agent(workspace))
    sys.exit(0 if result else 1)
EOF

# 设置权限
echo "设置文件权限..."
chmod +x test_runner.py
chmod +x run_demo.py
chmod +x test_rag_agent.py

# 运行基础验证
echo "运行环境验证..."
if command -v uv &> /dev/null; then
    cd "$PROJECT_ROOT"
    uv run python -c "import yaml, asyncio, psutil; print('✓ 基础依赖检查通过')"
    cd - > /dev/null
else
    python3 -c "import yaml, asyncio, psutil; print('✓ 基础依赖检查通过')"
fi

echo ""
echo "============================================"
echo "  设置完成！"
echo "============================================"
echo ""
echo "快速开始:"
echo "1. 运行RAG Code Agent测试:"
echo "   python3 test_rag_agent.py"
echo ""
echo "2. 运行演示脚本:"
echo "   python3 run_demo.py"
echo ""
echo "3. 运行入门级测试:"
echo "   python3 test_runner.py --level beginner"
echo ""
echo "4. 运行特定领域测试:"
echo "   python3 test_runner.py --domain algorithms"
echo ""
echo "5. 使用工作区路径运行测试:"
echo "   python3 test_runner.py --workspace $PROJECT_ROOT --level beginner"
echo ""
echo "6. 运行所有测试:"
echo "   python3 test_runner.py --level all --domain all"
echo ""
echo "7. 查看帮助:"
echo "   python3 test_runner.py --help"
echo ""
echo "测试报告将生成在 reports/ 目录中"
echo "日志文件将保存在 logs/ 目录中"
echo "RAG数据库位于: $PROJECT_ROOT/temp/rag_data/"
echo "Context数据库位于: $PROJECT_ROOT/temp/contexts.db"
echo "" 