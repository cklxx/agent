#!/bin/bash
"""
Code Agent 测试脚本

便于运行code agent的各种测试和演示
"""

set -e

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}$1${NC}"
    echo "=================================="
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 检查Python环境
check_environment() {
    print_header "检查环境"
    
    if ! command -v python3 &> /dev/null; then
        print_error "Python3 未找到"
        exit 1
    fi
    
    if [ ! -d ".venv" ] && [ ! -d "venv" ]; then
        print_warning "未检测到虚拟环境，建议使用 uv 创建虚拟环境"
    fi
    
    print_success "环境检查完成"
}

# 运行快速演示
run_quick_demo() {
    print_header "运行快速演示"
    
    local prompt=${1:-"创建一个简单的Python函数计算斐波那契数列"}
    echo "测试提示: $prompt"
    echo ""
    
    python examples/code_agent_reflection_demo.py quick "$prompt"
}

# 运行反思功能演示
run_reflection_demo() {
    print_header "运行反思功能演示"
    
    local scenario=${1:-"test_failure"}
    echo "演示场景: $scenario"
    echo ""
    
    python examples/code_agent_reflection_demo.py scenario "$scenario"
}

# 运行完整测试套件
run_full_tests() {
    print_header "运行完整测试套件"
    
    echo "这将运行所有测试用例，可能需要较长时间..."
    echo ""
    
    python tests/test_code_agent_workflow.py
}

# 运行所有反思演示
run_all_reflection_demos() {
    print_header "运行所有反思功能演示"
    
    echo "这将运行所有反思功能演示场景..."
    echo ""
    
    python examples/code_agent_reflection_demo.py
}

# 交互式测试
interactive_test() {
    print_header "交互式测试"
    
    echo "请输入您的测试提示："
    read -r user_prompt
    
    if [ -z "$user_prompt" ]; then
        print_warning "使用默认提示"
        user_prompt="创建一个简单的Python类来管理待办事项列表"
    fi
    
    echo ""
    echo "正在运行测试..."
    python tests/test_code_agent_workflow.py quick "$user_prompt"
}

# 显示帮助信息
show_help() {
    echo "Code Agent 测试脚本"
    echo ""
    echo "用法: $0 [命令] [参数]"
    echo ""
    echo "命令:"
    echo "  quick [提示]           - 运行快速演示 (默认: 斐波那契函数)"
    echo "  reflection [场景]      - 运行反思功能演示"
    echo "  full                   - 运行完整测试套件"
    echo "  all-demos             - 运行所有反思演示"
    echo "  interactive           - 交互式测试"
    echo "  help                  - 显示此帮助信息"
    echo ""
    echo "反思演示场景:"
    echo "  success               - 成功完成场景"
    echo "  test_failure          - 测试失败场景"
    echo "  incomplete            - 不完整实现场景"
    echo "  quality               - 代码质量问题场景"
    echo "  dependency            - 依赖问题场景"
    echo ""
    echo "示例:"
    echo "  $0 quick \"创建一个排序算法\""
    echo "  $0 reflection test_failure"
    echo "  $0 full"
}

# 主函数
main() {
    check_environment
    
    case "${1:-help}" in
        "quick")
            run_quick_demo "$2"
            ;;
        "reflection")
            run_reflection_demo "$2"
            ;;
        "full")
            run_full_tests
            ;;
        "all-demos")
            run_all_reflection_demos
            ;;
        "interactive")
            interactive_test
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            print_error "未知命令: $1"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# 运行主函数
main "$@" 