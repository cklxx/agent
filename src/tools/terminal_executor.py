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
    
    def __init__(self, additional_forbidden_commands: Optional[List[str]] = None):
        """
        初始化终端执行器
        
        Args:
            additional_forbidden_commands: 额外的禁止命令列表，会添加到默认黑名单中
        """
        # 默认黑名单 - 包含危险和破坏性命令
        default_forbidden = [
            # 文件删除和格式化
            'rm', 'rmdir', 'del', 'format', 'fdisk', 'mkfs', 'dd',
            
            # 系统控制
            'shutdown', 'reboot', 'halt', 'poweroff', 'init', 'systemctl',
            
            # 进程管理
            'kill', 'killall', 'pkill', 'killpg',
            
            # 用户和权限
            'passwd', 'sudo', 'su', 'chmod', 'chown', 'chgrp', 'usermod', 'userdel',
            
            # 网络和系统服务
            'iptables', 'firewall-cmd', 'ufw', 'service',
            
            # 包管理器的危险操作
            'apt-get remove', 'apt-get purge', 'yum remove', 'dnf remove',
            'pip uninstall', 'npm uninstall -g',
            
            # 系统配置
            'crontab', 'at', 'mount', 'umount', 'sysctl',
            
            # 危险的编辑器操作
            'vi /etc', 'vim /etc', 'nano /etc', 'emacs /etc',
            
            # 其他危险操作
            'history -c', 'history -w', 'exec', 'eval', 'source /dev'
        ]
        
        # 合并额外的禁止命令
        additional = additional_forbidden_commands or []
        self.forbidden_commands = default_forbidden + additional
        
        # 危险路径模式
        self.forbidden_paths = [
            '/etc/', '/bin/', '/sbin/', '/usr/bin/', '/usr/sbin/', '/boot/',
            '/dev/', '/proc/', '/sys/', '/root/', '/var/log/',
            'C:\\Windows\\', 'C:\\Program Files\\', 'C:\\Program Files (x86)\\',
            'C:\\System32\\', 'C:\\Users\\Administrator\\'
        ]
        
        logger.info(f"初始化终端执行器，黑名单包含 {len(self.forbidden_commands)} 个危险命令")
    
    def is_command_safe(self, command: str) -> bool:
        """检查命令是否安全可执行"""
        # 分离命令和参数
        cmd_parts = command.strip().split()
        if not cmd_parts:
            logger.warning("空命令，拒绝执行")
            return False
        
        base_command = cmd_parts[0]
        full_command = command.lower()
        
        # 检查基础命令是否在黑名单中
        if base_command in self.forbidden_commands:
            logger.warning(f"命令在黑名单中: {base_command}")
            return False
        
        # 检查完整命令是否包含黑名单中的危险组合
        for forbidden in self.forbidden_commands:
            if ' ' in forbidden and forbidden in full_command:
                logger.warning(f"命令包含危险操作: {forbidden}")
                return False
        
        # 检查是否操作危险路径
        for path in self.forbidden_paths:
            if path.lower() in full_command:
                logger.warning(f"命令尝试操作危险路径: {path}")
                return False
        
        # 检查是否包含危险的特殊字符和操作
        dangerous_patterns = [
            '$(', '`', '&&', '||', ';', 
            '>/dev/', '<(/dev/', 
            'curl|sh', 'wget|sh', 'bash <(',
            '>/etc/', '>>/etc/'
        ]
        for pattern in dangerous_patterns:
            if pattern in command:
                logger.warning(f"命令包含危险模式 '{pattern}': {command}")
                return False
        
        # 检查重定向到重要文件
        redirect_patterns = ['>', '>>']
        for pattern in redirect_patterns:
            if pattern in command:
                parts = command.split(pattern)
                if len(parts) > 1:
                    target = parts[-1].strip()
                    for dangerous_path in self.forbidden_paths:
                        if target.startswith(dangerous_path):
                            logger.warning(f"命令尝试重定向到危险路径: {target}")
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