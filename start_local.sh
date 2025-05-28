#!/bin/bash

# 定义颜色
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m' # 无颜色

# 创建临时目录存储进程ID
TEMP_DIR="./.temp_pids"
mkdir -p $TEMP_DIR

# 清理函数 - 在脚本退出时终止所有启动的进程
cleanup() {
    echo -e "\n${YELLOW}[*] 正在关闭所有服务...${NC}"
    
    # 终止所有保存的进程ID
    if [ -d "$TEMP_DIR" ]; then
        for pid_file in $TEMP_DIR/*.pid; do
            if [ -f "$pid_file" ]; then
                pid=$(cat "$pid_file")
                process_name=$(basename "$pid_file" .pid)
                echo -e "${YELLOW}[*] 正在终止 $process_name (PID: $pid)${NC}"
                kill $pid 2>/dev/null || true
            fi
        done
        rm -rf $TEMP_DIR
    fi
    
    echo -e "${GREEN}[✓] 所有服务已关闭${NC}"
    exit 0
}

# 注册清理函数在脚本退出时执行
trap cleanup EXIT INT TERM

# 输出标题
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}      Agent 项目本地服务启动脚本        ${NC}"
echo -e "${BLUE}========================================${NC}"

# 激活虚拟环境
echo -e "${BLUE}[*] 正在准备环境...${NC}"
source .venv/bin/activate 2>/dev/null || echo -e "${RED}[!] 虚拟环境未找到或无法激活${NC}"

# 从mcp.json读取配置
echo -e "${BLUE}[*] 正在读取MCP配置...${NC}"
MCP_SERVERS=$(cat mcp.json | grep -o '"command": "[^"]*"' | cut -d'"' -f4)

# 启动MCP服务器
echo -e "${BLUE}[*] 正在启动MCP服务器...${NC}"

# 启动Amap Maps MCP服务器
echo -e "${BLUE}[*] 启动 Amap Maps MCP 服务器...${NC}"
export AMAP_MAPS_API_KEY="7897d07c1c16a4da56995e13968b1641"
npx -y @amap/amap-maps-mcp-server > /dev/null 2>&1 &
echo $! > $TEMP_DIR/amap-maps.pid
echo -e "${GREEN}[✓] Amap Maps MCP 服务器已启动 (PID: $!)${NC}"

# 启动Playwright MCP服务器
echo -e "${BLUE}[*] 启动 Playwright MCP 服务器...${NC}"
npx -y @playwright/mcp@latest > /dev/null 2>&1 &
echo $! > $TEMP_DIR/playwright.pid
echo -e "${GREEN}[✓] Playwright MCP 服务器已启动 (PID: $!)${NC}"

# 启动Tavily MCP服务器
echo -e "${BLUE}[*] 启动 Tavily MCP 服务器...${NC}"
export TAVILY_API_KEY="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"
npx -y tavily-mcp@0.1.2 > /dev/null 2>&1 &
echo $! > $TEMP_DIR/tavily.pid
echo -e "${GREEN}[✓] Tavily MCP 服务器已启动 (PID: $!)${NC}"

# 等待服务器启动完成
echo -e "${BLUE}[*] 等待所有服务器启动完成...${NC}"
sleep 3

# 启动主应用程序
echo -e "${BLUE}[*] 启动主应用程序...${NC}"
echo -e "${GREEN}[✓] 所有服务已启动，开始运行主程序${NC}"
echo -e "${YELLOW}[!] 按 Ctrl+C 停止所有服务${NC}"
echo -e "${BLUE}========================================${NC}"

# 运行主程序
uv run main.py

# 注意：当主程序退出时，清理函数会自动被调用 