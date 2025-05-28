#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import subprocess
from pathlib import Path


class ColorPrint:
    """彩色终端输出类"""
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'

    @staticmethod
    def blue(text):
        return f"{ColorPrint.BLUE}{text}{ColorPrint.ENDC}"

    @staticmethod
    def green(text):
        return f"{ColorPrint.GREEN}{text}{ColorPrint.ENDC}"

    @staticmethod
    def yellow(text):
        return f"{ColorPrint.YELLOW}{text}{ColorPrint.ENDC}"

    @staticmethod
    def red(text):
        return f"{ColorPrint.RED}{text}{ColorPrint.ENDC}"


class SimpleRunner:
    """简化运行器，只运行主程序"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.absolute()
        
        # 预定义问题列表
        self.questions = [
            "海口3天旅游规划，住在喜来登酒店",
            "帮我写一个Python函数，计算斐波那契数列",
            "推荐5本科幻小说",
            "解释量子力学的基本原理",
            "如何做红烧肉？"
        ]
    
    def print_header(self):
        """打印标题"""
        print(f"{ColorPrint.blue('=' * 40)}")
        print(f"{ColorPrint.blue('      Agent 项目简化运行脚本       ')}")
        print(f"{ColorPrint.blue('=' * 40)}")
        print(f"{ColorPrint.blue('[*] 正在准备环境...')}")
        print(f"{ColorPrint.blue('[*] 启动主应用程序...')}")
        print(f"{ColorPrint.yellow('[!] 注意：此脚本不会启动任何MCP服务，请确保已手动启动所需服务')}")
        print(f"{ColorPrint.blue('=' * 40)}")
    
    def select_question(self):
        """让用户选择问题"""
        print(f"{ColorPrint.blue('可用问题列表:')}")
        for i, question in enumerate(self.questions, 1):
            print(f"{ColorPrint.green(f'{i}.')} {question}")
        
        print(f"{ColorPrint.blue('-' * 40)}")
        print(f"{ColorPrint.yellow(f'请选择问题编号(1-{len(self.questions)})，或输入0自定义问题:')}")
        
        try:
            choice = int(input("> "))
            if choice == 0:
                print(f"{ColorPrint.yellow('请输入您的问题:')}")
                custom_question = input("> ")
                return custom_question
            elif 1 <= choice <= len(self.questions):
                return self.questions[choice-1]
            else:
                print(f"{ColorPrint.red('[!] 无效选择，将使用默认问题')}")
                return self.questions[0]
        except ValueError:
            print(f"{ColorPrint.red('[!] 无效输入，将使用默认问题')}")
            return self.questions[0]
    
    def run_main_app(self, question):
        """运行主应用并传入问题"""
        print(f"{ColorPrint.blue('[*] 使用问题:')} {ColorPrint.green(question)}")
        print(f"{ColorPrint.blue('[*] 开始执行...')}")
        
        try:
            # 创建一个管道传递问题到主程序
            process = subprocess.Popen(
                ["uv", "run", "main.py"],
                stdin=subprocess.PIPE,
                text=True
            )
            
            # 发送问题到程序的标准输入
            process.communicate(input=question)
            
            return process.returncode == 0
        except Exception as e:
            print(f"{ColorPrint.red(f'[!] 运行主程序时出错: {e}')}")
            return False
    
    def run(self):
        """运行主流程"""
        self.print_header()
        question = self.select_question()
        self.run_main_app(question)


if __name__ == "__main__":
    runner = SimpleRunner()
    runner.run() 