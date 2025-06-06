# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
Terminal executor tool for safe command line operations.
"""

import subprocess
import os
import sys
import logging
from typing import Dict, List, Optional, Any
from langchain_core.tools import tool

# 设置日志
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 如果没有handler，添加一个console handler
if not logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('🔧 [Terminal] %(asctime)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)


class TerminalExecutor:
    """安全的命令行执行器"""
    
    def __init__(self, allowed_commands: Optional[List[str]] = None):
        """
        初始化终端执行器
        
        Args:
            allowed_commands: 允许执行的命令列表，如果为None则允许大部分安全命令
        """
        self.allowed_commands = allowed_commands or [
            'ls', 'pwd', 'cat', 'head', 'tail', 'grep', 'find', 'which', 'echo',
            'git', 'python', 'pip', 'npm', 'node', 'make', 'mkdir', 'touch',
            'cp', 'mv', 'wc', 'sort', 'uniq', 'diff', 'tree', 'du', 'df'
        ]
        self.forbidden_commands = [
            'rm', 'rmdir', 'del', 'format', 'shutdown', 'reboot', 'init',
            'kill', 'killall', 'passwd', 'sudo', 'su', 'chmod', 'chown'
        ]
        logger.info(f"初始化终端执行器，允许 {len(self.allowed_commands)} 个命令")
    
    def is_command_safe(self, command: str) -> bool:
        """检查命令是否安全可执行"""
        # 分离命令和参数
        cmd_parts = command.strip().split()
        if not cmd_parts:
            logger.warning("空命令，拒绝执行")
            return False
        
        base_command = cmd_parts[0]
        
        # 检查是否在禁止列表中
        if base_command in self.forbidden_commands:
            logger.warning(f"命令在禁止列表中: {base_command}")
            return False
        
        # 检查是否在允许列表中
        if base_command not in self.allowed_commands:
            logger.warning(f"命令不在允许列表中: {base_command}")
            return False
        
        # 检查是否包含危险的特殊字符
        dangerous_patterns = ['>', '>>', '|', '&', ';', '$(', '`']
        for pattern in dangerous_patterns:
            if pattern in command:
                logger.warning(f"命令包含危险字符 '{pattern}': {command}")
                return False
        
        logger.debug(f"命令安全检查通过: {base_command}")
        return True
    
    def execute_command(self, command: str, working_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        执行命令并返回结果
        
        Args:
            command: 要执行的命令
            working_dir: 工作目录
            
        Returns:
            包含执行结果的字典
        """
        logger.info(f"准备执行命令: {command}")
        
        if not self.is_command_safe(command):
            logger.error(f"命令安全检查失败: {command}")
            return {
                "success": False,
                "error": f"命令不安全或不被允许: {command}",
                "output": "",
                "return_code": -1
            }
        
        try:
            # 设置工作目录
            cwd = working_dir or os.getcwd()
            logger.debug(f"工作目录: {cwd}")
            
            # 执行命令
            logger.debug("开始执行命令...")
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=cwd,
                timeout=30  # 30秒超时
            )
            
            if result.returncode == 0:
                logger.info(f"命令执行成功，返回码: {result.returncode}")
                logger.debug(f"输出长度: {len(result.stdout)} 字符")
            else:
                logger.warning(f"命令执行失败，返回码: {result.returncode}")
                if result.stderr:
                    logger.warning(f"错误信息: {result.stderr[:200]}...")
            
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr,
                "return_code": result.returncode,
                "command": command,
                "working_dir": cwd
            }
            
        except subprocess.TimeoutExpired:
            logger.error(f"命令执行超时: {command}")
            return {
                "success": False,
                "error": "命令执行超时",
                "output": "",
                "return_code": -1,
                "command": command
            }
        except Exception as e:
            logger.error(f"执行命令时发生异常: {str(e)}")
            return {
                "success": False,
                "error": f"执行命令时发生错误: {str(e)}",
                "output": "",
                "return_code": -1,
                "command": command
            }


# 创建全局执行器实例
terminal_executor = TerminalExecutor()


@tool
def execute_terminal_command(command: str, working_directory: str = None) -> str:
    """
    安全地执行终端命令
    
    Args:
        command: 要执行的命令
        working_directory: 工作目录路径（可选）
    
    Returns:
        命令执行结果
    """
    logger.info(f"[Tool] 执行终端命令: {command}")
    result = terminal_executor.execute_command(command, working_directory)
    
    if result["success"]:
        logger.info(f"[Tool] 命令执行成功")
        return f"命令执行成功:\n输出: {result['output']}\n返回码: {result['return_code']}"
    else:
        logger.warning(f"[Tool] 命令执行失败: {result['error']}")
        return f"命令执行失败:\n错误: {result['error']}\n返回码: {result['return_code']}"


@tool  
def get_current_directory() -> str:
    """获取当前工作目录"""
    cwd = os.getcwd()
    logger.info(f"[Tool] 获取当前目录: {cwd}")
    return cwd


@tool
def list_directory_contents(path: str = ".") -> str:
    """
    列出目录内容
    
    Args:
        path: 目录路径，默认为当前目录
    
    Returns:
        目录内容列表
    """
    logger.info(f"[Tool] 列出目录内容: {path}")
    
    try:
        if not os.path.exists(path):
            logger.warning(f"[Tool] 路径不存在: {path}")
            return f"路径不存在: {path}"
        
        if not os.path.isdir(path):
            logger.warning(f"[Tool] 不是一个目录: {path}")
            return f"不是一个目录: {path}"
        
        contents = os.listdir(path)
        contents.sort()
        
        logger.info(f"[Tool] 找到 {len(contents)} 个项目")
        
        result = f"目录 {path} 的内容:\n"
        for item in contents:
            item_path = os.path.join(path, item)
            if os.path.isdir(item_path):
                result += f"[DIR]  {item}/\n"
            else:
                size = os.path.getsize(item_path)
                result += f"[FILE] {item} ({size} bytes)\n"
        
        logger.debug(f"[Tool] 目录列表长度: {len(result)} 字符")
        return result
    except Exception as e:
        logger.error(f"[Tool] 列出目录内容时发生错误: {str(e)}")
        return f"列出目录内容时发生错误: {str(e)}" 