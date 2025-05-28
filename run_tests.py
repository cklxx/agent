#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import subprocess
import argparse
from pathlib import Path


class TestRunner:
    """一键测试脚本，用于运行项目测试用例"""

    def __init__(self):
        self.project_root = Path(__file__).parent.absolute()
        self.tests_dir = self.project_root / "tests"

    def setup_environment(self):
        """准备测试环境"""
        print("\033[34m[*] 正在准备测试环境...\033[0m")
        
        # 检查是否安装了 pytest
        try:
            subprocess.run(
                ["python", "-m", "pytest", "--version"], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                check=True
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("\033[31m[!] 未找到 pytest, 正在安装...\033[0m")
            subprocess.run(["uv", "add", "--dev", "pytest"], check=True)

    def run_tests(self, test_type=None, verbose=False):
        """运行测试用例"""
        print("\033[34m[*] 开始运行测试...\033[0m")
        
        cmd = ["python", "-m", "pytest"]
        
        if verbose:
            cmd.append("-v")
            
        if test_type == "flow":
            print("\033[34m[*] 运行 Flow 测试\033[0m")
            cmd.append(str(self.tests_dir / "test_flow.py"))
        elif test_type == "api":
            print("\033[34m[*] 运行 API 服务器测试\033[0m")
            cmd.append(str(self.tests_dir / "test_api_server.py"))
        else:
            print("\033[34m[*] 运行所有测试\033[0m")
        
        try:
            subprocess.run(cmd, check=True)
            print("\033[32m[✓] 所有测试通过!\033[0m")
            return True
        except subprocess.CalledProcessError:
            print("\033[31m[✗] 测试失败!\033[0m")
            return False

    def print_header(self):
        """打印脚本标题"""
        print("\033[34m========================================\033[0m")
        print("\033[34m           Agent 项目测试脚本           \033[0m")
        print("\033[34m========================================\033[0m")


def main():
    parser = argparse.ArgumentParser(description="Agent 项目测试脚本")
    parser.add_argument("test_type", nargs="?", choices=["flow", "api"], 
                        help="指定要运行的测试类型: flow 或 api")
    parser.add_argument("-v", "--verbose", action="store_true", 
                        help="显示详细输出")
    
    args = parser.parse_args()
    
    runner = TestRunner()
    runner.print_header()
    runner.setup_environment()
    
    success = runner.run_tests(args.test_type, args.verbose)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main() 