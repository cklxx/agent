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
    
    def __init__(self, additional_forbidden_commands: Optional[List[str]] = None, additional_warning_commands: Optional[List[str]] = None):
        """
        初始化终端执行器
        
        Args:
            additional_forbidden_commands: 额外的禁止命令列表
            additional_warning_commands: 额外的警告命令列表
        """
        # 完全禁止的命令 - 危险且通常不必要
        default_forbidden = [
            # 系统级危险操作
            'format', 'fdisk', 'mkfs', 'dd',
            'shutdown', 'reboot', 'halt', 'poweroff', 'init',
            
            # 进程管理的危险操作
            'killall', 'pkill', 'killpg',
            
            # 用户和权限的危险操作
            'passwd', 'sudo', 'su', 'usermod', 'userdel',
            
            # 网络和防火墙
            'iptables', 'firewall-cmd', 'ufw',
            
            # 系统服务
            'systemctl', 'service',
            
            # 系统配置
            'crontab', 'at', 'mount', 'umount', 'sysctl',
            
            # 危险的包管理操作
            'apt-get remove', 'apt-get purge', 'yum remove', 'dnf remove',
            
            # 危险的编辑器操作
            'vi /etc', 'vim /etc', 'nano /etc', 'emacs /etc',
            
            # 其他危险操作
            'history -c', 'history -w', 'exec', 'eval', 'source /dev'
        ]
        
        # 警告但允许的命令 - 有风险但在开发中必要
        default_warning = [
            # 文件操作 - 可能删除重要文件但开发中常用
            'rm', 'rmdir', 'del',
            
            # 权限操作 - 有风险但开发中需要
            'chmod', 'chown', 'chgrp',
            
            # 进程管理 - 特定场景下需要
            'kill',
            
            # 包管理 - 开发中需要卸载包
            'pip uninstall', 'npm uninstall', 'yarn remove',
            
            # Git操作 - 有些操作有风险但必要
            'git reset --hard', 'git clean -fd', 'git push --force',
            
            # 网络操作 - 可能暴露信息但开发需要
            'curl', 'wget', 'ssh',
            
            # Docker操作 - 有些操作有风险
            'docker rm', 'docker rmi', 'docker system prune',
        ]
        
        # 合并额外的命令
        additional_forbidden = additional_forbidden_commands or []
        additional_warning = additional_warning_commands or []
        
        self.forbidden_commands = default_forbidden + additional_forbidden
        self.warning_commands = default_warning + additional_warning
        
        # 危险路径模式
        self.forbidden_paths = [
            '/etc/', '/bin/', '/sbin/', '/usr/bin/', '/usr/sbin/', '/boot/',
            '/dev/', '/proc/', '/sys/', '/root/', '/var/log/',
            'C:\\Windows\\', 'C:\\Program Files\\', 'C:\\Program Files (x86)\\',
            'C:\\System32\\', 'C:\\Users\\Administrator\\'
        ]
        
        # 警告路径模式 - 有风险但可能需要访问
        self.warning_paths = [
            '/home/', '/Users/', '~/', './.*', '../'
        ]
        
        logger.info(f"初始化终端执行器，禁止 {len(self.forbidden_commands)} 个命令，警告 {len(self.warning_commands)} 个命令")
    
    def check_command_safety(self, command: str) -> tuple[bool, str, str]:
        """
        检查命令安全性
        
        Args:
            command: 要检查的命令
            
        Returns:
            (is_allowed, safety_level, message)
            is_allowed: 是否允许执行
            safety_level: 'safe', 'warning', 'forbidden'
            message: 相关消息
        """
        # 分离命令和参数
        cmd_parts = command.strip().split()
        if not cmd_parts:
            return False, 'forbidden', "空命令"
        
        base_command = cmd_parts[0]
        full_command = command.lower()
        
        # 检查是否在完全禁止列表中
        if base_command in self.forbidden_commands:
            return False, 'forbidden', f"命令在禁止列表中: {base_command}"
        
        # 检查完整命令是否包含禁止的危险组合
        for forbidden in self.forbidden_commands:
            if ' ' in forbidden and forbidden in full_command:
                return False, 'forbidden', f"命令包含禁止的危险操作: {forbidden}"
        
        # 检查是否操作禁止的危险路径
        for path in self.forbidden_paths:
            if path.lower() in full_command:
                return False, 'forbidden', f"命令尝试操作禁止的危险路径: {path}"
        
        # 检查是否包含禁止的危险模式
        forbidden_patterns = [
            '$(', '`', '&&', '||', ';', 
            '>/dev/', '<(/dev/', 
            'curl|sh', 'wget|sh', 'bash <(',
            '>/etc/', '>>/etc/'
        ]
        for pattern in forbidden_patterns:
            if pattern in command:
                return False, 'forbidden', f"命令包含禁止的危险模式: {pattern}"
        
        # 检查重定向到禁止路径
        redirect_patterns = ['>', '>>']
        for pattern in redirect_patterns:
            if pattern in command:
                parts = command.split(pattern)
                if len(parts) > 1:
                    target = parts[-1].strip()
                    for dangerous_path in self.forbidden_paths:
                        if target.startswith(dangerous_path):
                            return False, 'forbidden', f"命令尝试重定向到禁止路径: {target}"
        
        # 检查是否在警告列表中
        if base_command in self.warning_commands:
            return True, 'warning', f"警告：{base_command} 命令有潜在风险，请谨慎使用"
        
        # 检查完整命令是否包含警告的操作
        for warning in self.warning_commands:
            if ' ' in warning and warning in full_command:
                return True, 'warning', f"警告：命令包含潜在风险操作: {warning}"
        
        # 检查是否操作警告路径
        for path in self.warning_paths:
            if path in full_command:
                return True, 'warning', f"警告：命令操作敏感路径: {path}"
        
        # 检查其他警告模式
        warning_patterns = [
            '--force', '-f', '--hard', '--delete', 'rm -rf'
        ]
        for pattern in warning_patterns:
            if pattern in command:
                return True, 'warning', f"警告：命令使用了潜在危险选项: {pattern}"
        
        return True, 'safe', "命令安全"
    
    def is_command_safe(self, command: str) -> bool:
        """检查命令是否安全可执行（向后兼容）"""
        is_allowed, safety_level, message = self.check_command_safety(command)
        
        if safety_level == 'forbidden':
            logger.warning(f"🚫 {message}")
        elif safety_level == 'warning':
            logger.warning(f"⚠️  {message}")
        else:
            logger.debug(f"✅ {message}: {command.split()[0]}")
        
        return is_allowed
    
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
    
    # 检查命令安全性并提供详细信息
    is_allowed, safety_level, safety_message = terminal_executor.check_command_safety(command)
    
    if not is_allowed:
        logger.error(f"[Tool] 命令被拒绝: {safety_message}")
        return f"❌ 命令被拒绝:\n{safety_message}\n\n建议：请使用更安全的替代命令或联系管理员。"
    
    # 如果有安全警告，先显示警告信息
    warning_info = ""
    if safety_level == 'warning':
        warning_info = f"⚠️  安全提醒: {safety_message}\n\n"
        logger.warning(f"[Tool] {safety_message}")
    
    result = terminal_executor.execute_command(command, working_directory)
    
    if result["success"]:
        logger.info(f"[Tool] 命令执行成功")
        return f"{warning_info}✅ 命令执行成功:\n输出: {result['output']}\n返回码: {result['return_code']}"
    else:
        logger.warning(f"[Tool] 命令执行失败: {result['error']}")
        return f"{warning_info}❌ 命令执行失败:\n错误: {result['error']}\n返回码: {result['return_code']}"


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