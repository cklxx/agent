#!/bin/bash

# 定义颜色
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # 无颜色

# 输出标题
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}           Agent 项目测试脚本           ${NC}"
echo -e "${BLUE}========================================${NC}"

# 激活虚拟环境
echo -e "${BLUE}[*] 正在准备测试环境...${NC}"
source .venv/bin/activate 2>/dev/null || echo -e "${RED}[!] 虚拟环境未找到或无法激活${NC}"

# 检查依赖是否安装
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}[!] 未找到 pytest, 正在安装...${NC}"
    uv add --dev pytest
fi

# 处理命令行参数
if [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
    echo -e "${GREEN}用法:${NC}"
    echo -e "  ./run_tests.sh         - 运行所有测试"
    echo -e "  ./run_tests.sh flow    - 只运行 flow 测试"
    echo -e "  ./run_tests.sh api     - 只运行 API 服务器测试"
    echo -e "  ./run_tests.sh -v      - 运行所有测试（详细输出）"
    echo -e "  ./run_tests.sh -h      - 显示帮助信息"
    exit 0
fi

# 设置 pytest 选项
PYTEST_OPTS=""
if [ "$1" == "-v" ] || [ "$1" == "--verbose" ]; then
    PYTEST_OPTS="-v"
fi

# 运行测试
echo -e "${BLUE}[*] 开始运行测试...${NC}"

case "$1" in
    "flow")
        echo -e "${BLUE}[*] 运行 Flow 测试${NC}"
        python -m pytest tests/test_flow.py $PYTEST_OPTS
        ;;
    "api")
        echo -e "${BLUE}[*] 运行 API 服务器测试${NC}"
        python -m pytest tests/test_api_server.py $PYTEST_OPTS
        ;;
    *)
        echo -e "${BLUE}[*] 运行所有测试${NC}"
        python -m pytest $PYTEST_OPTS
        ;;
esac

# 检查测试结果
if [ $? -eq 0 ]; then
    echo -e "${GREEN}[✓] 所有测试通过!${NC}"
else
    echo -e "${RED}[✗] 测试失败!${NC}"
    exit 1
fi

echo -e "${BLUE}========================================${NC}" 