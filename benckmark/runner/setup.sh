#!/bin/bash

# AI Agent Benchmark 测试环境快速设置脚本

set -e

echo "============================================"
echo "  AI Agent Benchmark 测试环境设置"
echo "============================================"

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
if [ "$CURRENT_DIR" != "benchmark" ]; then
    echo "错误: 请在temp/benchmark目录下运行此脚本"
    exit 1
fi

# 创建虚拟环境（可选）
if [ ! -d "venv" ]; then
    echo "创建Python虚拟环境..."
    python3 -m venv venv
fi

echo "激活虚拟环境..."
source venv/bin/activate

# 升级pip
echo "升级pip..."
pip install --upgrade pip

# 安装依赖
echo "安装依赖包..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo "警告: requirements.txt 文件不存在，手动安装基础依赖..."
    pip install PyYAML pytest asyncio psutil
fi

# 创建必要的目录
echo "创建必要的目录结构..."
mkdir -p logs
mkdir -p sandbox
mkdir -p reports
mkdir -p test_data

# 设置权限
echo "设置文件权限..."
chmod +x test_runner.py
chmod +x run_demo.py

# 运行基础验证
echo "运行环境验证..."
python3 -c "import yaml, asyncio, psutil; print('✓ 基础依赖检查通过')"

echo ""
echo "============================================"
echo "  设置完成！"
echo "============================================"
echo ""
echo "快速开始:"
echo "1. 运行演示脚本:"
echo "   python3 run_demo.py"
echo ""
echo "2. 运行入门级测试:"
echo "   python3 test_runner.py --level beginner"
echo ""
echo "3. 运行特定领域测试:"
echo "   python3 test_runner.py --domain algorithms"
echo ""
echo "4. 运行所有测试:"
echo "   python3 test_runner.py --level all --domain all"
echo ""
echo "5. 查看帮助:"
echo "   python3 test_runner.py --help"
echo ""
echo "测试报告将生成在 reports/ 目录中"
echo "日志文件将保存在 logs/ 目录中"
echo "" 