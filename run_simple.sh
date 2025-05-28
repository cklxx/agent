#!/bin/bash

# 定义颜色
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m' # 无颜色

# 输出标题
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}      Agent 项目简化运行脚本            ${NC}"
echo -e "${BLUE}========================================${NC}"

# 激活虚拟环境
echo -e "${BLUE}[*] 正在准备环境...${NC}"
source .venv/bin/activate 2>/dev/null || echo -e "${RED}[!] 虚拟环境未找到或无法激活${NC}"

# 运行主程序
echo -e "${BLUE}[*] 启动主应用程序...${NC}"
echo -e "${YELLOW}[!] 注意：此脚本不会启动任何MCP服务，请确保已手动启动所需服务${NC}"
echo -e "${BLUE}========================================${NC}"

# 定义问题列表
declare -a QUESTIONS=(
    "海口3天旅游规划，住在喜来登酒店" 
    "帮我写一个Python函数，计算斐波那契数列"
    "推荐5本科幻小说"
    "解释量子力学的基本原理"
    "如何做红烧肉？"
)

# 显示问题列表
echo -e "${BLUE}可用问题列表:${NC}"
for i in "${!QUESTIONS[@]}"; do
    echo -e "${GREEN}$((i+1)).${NC} ${QUESTIONS[$i]}"
done
echo -e "${BLUE}----------------------------------------${NC}"
echo -e "${YELLOW}请选择问题编号(1-${#QUESTIONS[@]})，或输入0自定义问题:${NC}"
read -p "> " choice

# 处理用户选择
if [[ $choice -eq 0 ]]; then
    echo -e "${YELLOW}请输入您的问题:${NC}"
    read -p "> " custom_question
    QUESTION="$custom_question"
elif [[ $choice -ge 1 && $choice -le ${#QUESTIONS[@]} ]]; then
    QUESTION="${QUESTIONS[$((choice-1))]}"
else
    echo -e "${RED}[!] 无效选择，将使用默认问题${NC}"
    QUESTION="${QUESTIONS[0]}"
fi

echo -e "${BLUE}[*] 使用问题: ${GREEN}$QUESTION${NC}"
echo -e "${BLUE}[*] 开始执行...${NC}"

# 使用echo将问题传递给主程序
echo "$QUESTION" | uv run main.py 