#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import time
import signal
import subprocess
import json
import shutil
import atexit
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


class LocalRunner:
    """一键本地测试运行器"""

    def __init__(self):
        self.project_root = Path(__file__).parent.absolute()
        self.temp_dir = self.project_root / ".temp_pids"
        self.processes = {}
        
        # 创建临时目录
        if not self.temp_dir.exists():
            self.temp_dir.mkdir()
        
        # 注册退出处理函数
        atexit.register(self.cleanup)

    def cleanup(self):
        """清理所有启动的进程"""
        print(f"\n{ColorPrint.yellow('[*] 正在关闭所有服务...')}")
        
        for name, process in self.processes.items():
            if process.poll() is None:  # 如果进程仍在运行
                print(f"{ColorPrint.yellow(f'[*] 正在终止 {name} (PID: {process.pid})')}")
                try:
                    process.terminate()
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
        
        # 删除临时目录
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
        
        print(f"{ColorPrint.green('[✓] 所有服务已关闭')}")

    def load_mcp_config(self):
        """加载MCP配置"""
        mcp_config_path = self.project_root / "mcp.json"
        print(f"{ColorPrint.blue('[*] 正在读取MCP配置...')}")
        
        if not mcp_config_path.exists():
            print(f"{ColorPrint.red('[!] mcp.json 不存在，请确保已正确配置')}")
            sys.exit(1)
        
        with open(mcp_config_path, 'r') as f:
            return json.load(f)

    def start_mcp_servers(self):
        """启动所有MCP服务器"""
        print(f"{ColorPrint.blue('[*] 正在启动MCP服务器...')}")
        
        # 启动Amap Maps MCP服务器
        print(f"{ColorPrint.blue('[*] 启动 Amap Maps MCP 服务器...')}")
        env = os.environ.copy()
        env['AMAP_MAPS_API_KEY'] = "7897d07c1c16a4da56995e13968b1641"
        amap_process = subprocess.Popen(
            ["npx", "-y", "@amap/amap-maps-mcp-server"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env
        )
        self.processes['amap-maps'] = amap_process
        print(f"{ColorPrint.green(f'[✓] Amap Maps MCP 服务器已启动 (PID: {amap_process.pid})')}")
        
        # 启动Playwright MCP服务器
        print(f"{ColorPrint.blue('[*] 启动 Playwright MCP 服务器...')}")
        playwright_process = subprocess.Popen(
            ["npx", "-y", "@playwright/mcp@latest"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        self.processes['playwright'] = playwright_process
        print(f"{ColorPrint.green(f'[✓] Playwright MCP 服务器已启动 (PID: {playwright_process.pid})')}")
        
        # 启动Tavily MCP服务器
        print(f"{ColorPrint.blue('[*] 启动 Tavily MCP 服务器...')}")
        env = os.environ.copy()
        env['TAVILY_API_KEY'] = "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"
        tavily_process = subprocess.Popen(
            ["npx", "-y", "tavily-mcp@0.1.2"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env
        )
        self.processes['tavily'] = tavily_process
        print(f"{ColorPrint.green(f'[✓] Tavily MCP 服务器已启动 (PID: {tavily_process.pid})')}")
        
        # 等待服务器启动
        print(f"{ColorPrint.blue('[*] 等待所有服务器启动完成...')}")
        time.sleep(3)

    def run_main_app(self):
        """运行主应用程序"""
        print(f"{ColorPrint.blue('[*] 启动主应用程序...')}")
        print(f"{ColorPrint.green('[✓] 所有服务已启动，开始运行主程序')}")
        print(f"{ColorPrint.yellow('[!] 按 Ctrl+C 停止所有服务')}")
        print(f"{ColorPrint.blue('=' * 40)}")
        
        try:
            # 运行主程序并等待其完成
            subprocess.run(["uv", "run", "main.py"], check=True)
        except KeyboardInterrupt:
            print(f"\n{ColorPrint.yellow('[!] 收到终止信号，正在关闭...')}")
        except Exception as e:
            print(f"{ColorPrint.red(f'[!] 运行主程序时出错: {e}')}")

    def run(self):
        """运行所有服务"""
        # 打印标题
        print(f"{ColorPrint.blue('=' * 40)}")
        print(f"{ColorPrint.blue('      Agent 项目本地服务启动脚本       ')}")
        print(f"{ColorPrint.blue('=' * 40)}")
        
        # 加载配置
        self.load_mcp_config()
        
        # 启动服务器
        self.start_mcp_servers()
        
        # 运行主应用
        self.run_main_app()


def signal_handler(sig, frame):
    """处理终止信号"""
    print(f"\n{ColorPrint.yellow('[!] 收到终止信号，正在关闭...')}")
    sys.exit(0)


if __name__ == "__main__":
    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 启动服务
    runner = LocalRunner()
    runner.run() 