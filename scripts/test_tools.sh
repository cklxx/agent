#!/bin/bash

# 工具测试脚本
# 使用方法: ./scripts/test_tools.sh [选项]

set -e

# 脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 帮助信息
show_help() {
    echo "工具测试脚本"
    echo ""
    echo "使用方法:"
    echo "  $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -a, --all          运行所有工具测试"
    echo "  -w, --workspace    运行workspace工具测试"
    echo "  -f, --file-edit    运行文件编辑工具测试"
    echo "  -s, --file-system  运行文件系统工具测试"
    echo "  -r, --architect    运行架构工具测试"
    echo "  -b, --bash         运行bash工具测试"
    echo "  -m, --maps         运行地图工具测试"
    echo "  -v, --verbose      详细输出"
    echo "  -q, --quick        快速测试（只运行基础测试）"
    echo "  -h, --help         显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 --all           # 运行所有测试"
    echo "  $0 -w -v           # 详细模式运行workspace测试"
    echo "  $0 --quick         # 快速测试"
}

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查依赖
check_dependencies() {
    log_info "检查依赖..."
    
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 未安装"
        exit 1
    fi
    
    if ! python3 -m pytest --version &> /dev/null; then
        log_error "pytest 未安装，正在安装..."
        pip install pytest
    fi
    
    log_success "依赖检查完成"
}

# 运行特定测试
run_test() {
    local test_file="$1"
    local test_name="$2"
    local verbose="$3"
    
    local test_path="$PROJECT_ROOT/tests/$test_file"
    
    if [[ ! -f "$test_path" ]]; then
        log_warning "测试文件不存在: $test_file"
        return 1
    fi
    
    log_info "运行 $test_name 测试..."
    
    local cmd="cd '$PROJECT_ROOT' && python3 -m pytest '$test_path'"
    
    if [[ "$verbose" == "true" ]]; then
        cmd="$cmd -v"
    else
        cmd="$cmd -q"
    fi
    
    if eval "$cmd"; then
        log_success "$test_name 测试通过"
        return 0
    else
        log_error "$test_name 测试失败"
        return 1
    fi
}

# 主函数
main() {
    local run_all=false
    local run_workspace=false
    local run_file_edit=false
    local run_file_system=false
    local run_architect=false
    local run_bash=false
    local run_maps=false
    local verbose=false
    local quick=false
    
    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -a|--all)
                run_all=true
                shift
                ;;
            -w|--workspace)
                run_workspace=true
                shift
                ;;
            -f|--file-edit)
                run_file_edit=true
                shift
                ;;
            -s|--file-system)
                run_file_system=true
                shift
                ;;
            -r|--architect)
                run_architect=true
                shift
                ;;
            -b|--bash)
                run_bash=true
                shift
                ;;
            -m|--maps)
                run_maps=true
                shift
                ;;
            -v|--verbose)
                verbose=true
                shift
                ;;
            -q|--quick)
                quick=true
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                log_error "未知选项: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # 如果没有指定任何测试，显示帮助
    if [[ "$run_all" == false && "$run_workspace" == false && "$run_file_edit" == false && 
          "$run_file_system" == false && "$run_architect" == false && "$run_bash" == false && 
          "$run_maps" == false && "$quick" == false ]]; then
        show_help
        exit 1
    fi
    
    # 检查依赖
    check_dependencies
    
    log_info "开始运行工具测试..."
    log_info "项目根目录: $PROJECT_ROOT"
    echo ""
    
    local failed_tests=0
    local total_tests=0
    
    # 快速测试模式
    if [[ "$quick" == true ]]; then
        total_tests=$((total_tests + 1))
        if ! run_test "test_tools.py" "基础工具" "$verbose"; then
            failed_tests=$((failed_tests + 1))
        fi
    fi
    
    # 运行指定的测试
    if [[ "$run_all" == true || "$run_workspace" == true ]]; then
        total_tests=$((total_tests + 1))
        if ! run_test "test_workspace_tools.py" "Workspace工具" "$verbose"; then
            failed_tests=$((failed_tests + 1))
        fi
    fi
    
    if [[ "$run_all" == true || "$run_file_edit" == true ]]; then
        total_tests=$((total_tests + 1))
        if ! run_test "test_file_edit_tools.py" "文件编辑工具" "$verbose"; then
            failed_tests=$((failed_tests + 1))
        fi
    fi
    
    if [[ "$run_all" == true || "$run_file_system" == true ]]; then
        total_tests=$((total_tests + 1))
        if ! run_test "test_file_system_tools.py" "文件系统工具" "$verbose"; then
            failed_tests=$((failed_tests + 1))
        fi
    fi
    
    if [[ "$run_all" == true || "$run_architect" == true ]]; then
        total_tests=$((total_tests + 1))
        if ! run_test "test_architect_tools.py" "架构工具" "$verbose"; then
            failed_tests=$((failed_tests + 1))
        fi
    fi
    
    if [[ "$run_all" == true || "$run_bash" == true ]]; then
        total_tests=$((total_tests + 1))
        if ! run_test "test_bash_tool.py" "Bash工具" "$verbose"; then
            failed_tests=$((failed_tests + 1))
        fi
    fi
    
    if [[ "$run_all" == true || "$run_maps" == true ]]; then
        total_tests=$((total_tests + 1))
        if ! run_test "test_maps_tools.py" "地图工具" "$verbose"; then
            failed_tests=$((failed_tests + 1))
        fi
    fi
    
    # 打印总结
    echo ""
    echo "==================== 测试总结 ===================="
    echo "总测试数: $total_tests"
    echo "通过: $((total_tests - failed_tests))"
    echo "失败: $failed_tests"
    
    if [[ $failed_tests -eq 0 ]]; then
        log_success "🎉 所有测试都通过了!"
        exit 0
    else
        log_error "💔 有 $failed_tests 个测试失败"
        exit 1
    fi
}

# 运行主函数
main "$@" 