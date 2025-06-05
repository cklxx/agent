#!/bin/bash

# 演示脚本：在 /Users/ckl/code/code-agent-test 目录下运行 Code Agent CLI

echo "🎯 Code Agent CLI - 指定目录运行演示"
echo "=" * 50

TARGET_DIR="/Users/ckl/code/code-agent-test"

echo "📍 目标工作目录: $TARGET_DIR"

# 检查目标目录是否存在
if [ ! -d "$TARGET_DIR" ]; then
    echo "❌ 目标目录不存在，正在创建..."
    mkdir -p "$TARGET_DIR"
    echo "✅ 目录创建成功"
fi

echo ""
echo "🚀 可用的示例命令："
echo ""
echo "1. 创建一个简单的Python项目："
echo "   ./code_agent --task \"Create a simple Python calculator project with basic math operations\" --working-directory $TARGET_DIR"
echo ""
echo "2. 查看目标目录内容："
echo "   ./code_agent --task \"List all files and directories in the current working directory\" --working-directory $TARGET_DIR"
echo ""
echo "3. 创建一个Web应用："
echo "   ./code_agent --task \"Create a simple Flask web application with a homepage\" --working-directory $TARGET_DIR"
echo ""
echo "4. 创建项目结构："
echo "   ./code_agent --task \"Create a standard Python project structure with src, tests, and docs directories\" --working-directory $TARGET_DIR"
echo ""

# 提供交互式选择
echo "请选择要执行的操作："
echo "1) 创建Python计算器项目"
echo "2) 查看目录内容"
echo "3) 创建Flask Web应用"
echo "4) 创建项目结构"
echo "5) 自定义任务"
echo "6) 退出"
echo ""

read -p "请输入选择 (1-6): " choice

case $choice in
    1)
        echo "🚀 执行: 创建Python计算器项目"
        ./code_agent --task "Create a simple Python calculator project with basic math operations (add, subtract, multiply, divide). Include a main.py file with a simple command-line interface." --working-directory "$TARGET_DIR"
        ;;
    2)
        echo "🚀 执行: 查看目录内容"
        ./code_agent --task "List all files and directories in the current working directory with detailed information" --working-directory "$TARGET_DIR"
        ;;
    3)
        echo "🚀 执行: 创建Flask Web应用"
        ./code_agent --task "Create a simple Flask web application with a homepage that displays 'Hello, World!' and includes basic HTML template" --working-directory "$TARGET_DIR"
        ;;
    4)
        echo "🚀 执行: 创建项目结构"
        ./code_agent --task "Create a standard Python project structure with src/, tests/, docs/ directories and a README.md file" --working-directory "$TARGET_DIR"
        ;;
    5)
        read -p "请输入自定义任务描述: " custom_task
        echo "🚀 执行: $custom_task"
        ./code_agent --task "$custom_task" --working-directory "$TARGET_DIR"
        ;;
    6)
        echo "👋 退出演示"
        exit 0
        ;;
    *)
        echo "❌ 无效选择"
        exit 1
        ;;
esac

echo ""
echo "✅ 任务执行完成！"
echo "📍 请检查目录: $TARGET_DIR" 