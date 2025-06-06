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

import threading
import time
import queue
import uuid
from datetime import datetime
from collections import defaultdict

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


class BackgroundTask:
    """后台任务管理类"""
    def __init__(self, task_id: str, command: str, process: subprocess.Popen, working_dir: str):
        self.task_id = task_id
        self.command = command
        self.process = process
        self.working_dir = working_dir
        self.start_time = datetime.now()
        self.status = "running"
        self.output_buffer = []
        self.error_buffer = []
        self.last_output_time = datetime.now()
        self._lock = threading.Lock()
        
    def add_output(self, line: str, is_error: bool = False):
        """添加输出行"""
        with self._lock:
            timestamp = datetime.now().strftime("%H:%M:%S")
            formatted_line = f"[{timestamp}] {line}"
            if is_error:
                self.error_buffer.append(formatted_line)
            else:
                self.output_buffer.append(formatted_line)
            self.last_output_time = datetime.now()
            
            # 保持缓冲区大小限制
            if len(self.output_buffer) > 100:
                self.output_buffer = self.output_buffer[-100:]
            if len(self.error_buffer) > 50:
                self.error_buffer = self.error_buffer[-50:]
    
    def get_recent_output(self, lines: int = 10) -> Dict[str, List[str]]:
        """获取最近的输出"""
        with self._lock:
            return {
                "stdout": self.output_buffer[-lines:] if self.output_buffer else [],
                "stderr": self.error_buffer[-lines:] if self.error_buffer else []
            }
    
    def get_status_info(self) -> Dict[str, Any]:
        """获取任务状态信息"""
        with self._lock:
            runtime = datetime.now() - self.start_time
            return {
                "task_id": self.task_id,
                "command": self.command,
                "status": self.status,
                "working_dir": self.working_dir,
                "start_time": self.start_time.strftime("%Y-%m-%d %H:%M:%S"),
                "runtime_seconds": runtime.total_seconds(),
                "output_lines": len(self.output_buffer),
                "error_lines": len(self.error_buffer),
                "last_output": self.last_output_time.strftime("%H:%M:%S"),
                "pid": self.process.pid if self.process else None
            }
    
    def terminate(self):
        """终止任务"""
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.status = "terminated"
            return True
        return False


class TerminalExecutor:
    """安全的命令行执行器"""
    
    def __init__(self, additional_forbidden_commands: Optional[List[str]] = None, additional_warning_commands: Optional[List[str]] = None):
        """
        初始化终端执行器
        
        Args:
            additional_forbidden_commands: 额外的禁止命令列表
            additional_warning_commands: 额外的警告命令列表
        """
        # 后台任务管理
        self.background_tasks: Dict[str, BackgroundTask] = {}
        self.task_lock = threading.Lock()
        self.monitor_thread = None
        self.monitor_running = False
        self._start_monitor_thread()
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
    
    def _is_dangerous_path(self, path_in_command: str) -> tuple[bool, str]:
        """
        智能检测路径是否危险
        
        Args:
            path_in_command: 命令中的路径字符串
            
        Returns:
            (is_dangerous, reason)
        """
        # 定义安全的项目路径模式（优先检查）
        safe_project_patterns = [
            # 虚拟环境路径
            '.venv', 'venv/', './venv', 'env/', '.env/', 
            'virtualenv/', '.virtualenv/', 'conda/', '.conda/',
            # 包管理器相关路径  
            'node_modules/.bin/', './.bin/', './node_modules/',
            # 项目目录相对路径
            './bin/', '../bin/', './env/', '../env/',
            # 用户主目录下的开发环境
            '~/venv', '~/.local/', '~/anaconda', '~/miniconda'
        ]
        
        # 首先检查是否是安全的项目路径
        for safe_pattern in safe_project_patterns:
            if safe_pattern in path_in_command:
                return False, f"安全的项目路径: {safe_pattern}"
        
        # 定义真正危险的系统路径模式（绝对路径）
        dangerous_system_paths = [
            '/etc/', '/bin/', '/sbin/', '/usr/bin/', '/usr/sbin/', '/boot/',
            '/dev/', '/proc/', '/sys/', '/root/', '/var/log/'
        ]
        
        # 检查是否是危险的系统路径
        lower_command = path_in_command.lower()
        for dangerous_path in dangerous_system_paths:
            # 检查各种可能的危险路径模式
            if (lower_command.startswith(dangerous_path.lower()) or  # 命令以危险路径开头
                f" {dangerous_path.lower()}" in lower_command or     # 危险路径作为参数
                f" {dangerous_path.lower().rstrip('/')}" in lower_command):  # 去掉尾部斜杠的路径
                return True, f"危险的系统路径: {dangerous_path}"
        
        return False, "普通路径"

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

        # 使用智能路径检测
        is_dangerous_path, path_reason = self._is_dangerous_path(command)
        if is_dangerous_path:
            return False, 'forbidden', f"命令尝试操作禁止的危险路径: {path_reason}"
        
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
    
    def _start_monitor_thread(self):
        """启动监控线程"""
        if not self.monitor_running:
            self.monitor_running = True
            self.monitor_thread = threading.Thread(target=self._monitor_background_tasks, daemon=True)
            self.monitor_thread.start()
            logger.debug("🔄 后台任务监控线程已启动")
    
    def _monitor_background_tasks(self):
        """监控后台任务"""
        while self.monitor_running:
            try:
                with self.task_lock:
                    completed_tasks = []
                    tasks_to_clean = []
                    
                    for task_id, task in self.background_tasks.items():
                        # 检查进程是否结束
                        if task.process.poll() is not None and task.status == "running":
                            # 只在状态第一次变化时打印日志
                            old_status = task.status
                            task.status = "completed" if task.process.returncode == 0 else "failed"
                            completed_tasks.append(task_id)
                            logger.info(f"🏁 后台任务完成: {task_id} - {task.command} (返回码: {task.process.returncode})")
                        
                        # 检查是否需要清理（完成超过5分钟的任务）
                        if task.status in ["completed", "failed", "terminated"]:
                            if (datetime.now() - task.start_time).total_seconds() > 300:  # 5分钟后清理
                                tasks_to_clean.append(task_id)
                    
                    # 清理已完成的任务
                    for task_id in tasks_to_clean:
                        del self.background_tasks[task_id]
                        logger.debug(f"🗑️ 清理完成任务: {task_id}")
                
                time.sleep(2)  # 每2秒检查一次
            except Exception as e:
                logger.error(f"❌ 监控线程异常: {e}")
                time.sleep(5)
    
    def _read_process_output(self, task: BackgroundTask):
        """读取进程输出的线程函数"""
        def read_stdout():
            try:
                for line in iter(task.process.stdout.readline, ''):
                    if line:
                        task.add_output(line.strip(), is_error=False)
                        logger.debug(f"📤 [{task.task_id}] {line.strip()}")
            except Exception as e:
                logger.error(f"❌ 读取stdout异常: {e}")
        
        def read_stderr():
            try:
                for line in iter(task.process.stderr.readline, ''):
                    if line:
                        task.add_output(line.strip(), is_error=True)
                        logger.warning(f"📥 [{task.task_id}] {line.strip()}")
            except Exception as e:
                logger.error(f"❌ 读取stderr异常: {e}")
        
        # 启动读取线程
        stdout_thread = threading.Thread(target=read_stdout, daemon=True)
        stderr_thread = threading.Thread(target=read_stderr, daemon=True)
        stdout_thread.start()
        stderr_thread.start()
    
    def execute_command_background(self, command: str, working_dir: Optional[str] = None) -> Dict[str, Any]:
        """在后台执行命令"""
        logger.info(f"🚀 准备在后台执行命令: {command}")
        
        if not self.is_command_safe(command):
            logger.error(f"命令安全检查失败: {command}")
            return {
                "success": False,
                "error": f"命令不安全或不被允许: {command}",
                "task_id": None
            }
        
        try:
            # 设置工作目录
            cwd = working_dir or os.getcwd()
            logger.info(f"🌐 后台执行环境: {cwd}")
            
            # 增强命令以支持虚拟环境
            enhanced_command = self._enhance_command_for_venv(command, cwd)
            if enhanced_command != command:
                logger.info(f"🔄 后台命令已增强虚拟环境支持")
            
            # 生成任务ID
            task_id = f"task_{uuid.uuid4().hex[:8]}"
            
            # 启动进程
            process = subprocess.Popen(
                enhanced_command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=cwd,
                bufsize=1,  # 行缓冲
                universal_newlines=True
            )
            
            # 创建后台任务（保存原始命令便于显示）
            task = BackgroundTask(task_id, command, process, cwd)
            
            with self.task_lock:
                self.background_tasks[task_id] = task
            
            # 启动输出读取线程
            self._read_process_output(task)
            
            logger.info(f"✅ 后台任务已启动: {task_id} (PID: {process.pid})")
            
            return {
                "success": True,
                "task_id": task_id,
                "pid": process.pid,
                "command": command,
                "working_dir": cwd,
                "message": f"命令已在后台启动，任务ID: {task_id}"
            }
            
        except Exception as e:
            logger.error(f"❌ 启动后台命令时发生异常: {str(e)}")
            return {
                "success": False,
                "error": f"启动后台命令时发生错误: {str(e)}",
                "task_id": None
            }
    
    def get_task_status(self, task_id: str = None) -> Dict[str, Any]:
        """获取任务状态"""
        with self.task_lock:
            if task_id:
                # 获取特定任务状态
                if task_id in self.background_tasks:
                    task = self.background_tasks[task_id]
                    return {
                        "success": True,
                        "task": task.get_status_info(),
                        "recent_output": task.get_recent_output()
                    }
                else:
                    return {
                        "success": False,
                        "error": f"任务 {task_id} 不存在"
                    }
            else:
                # 获取所有任务状态
                tasks = []
                for tid, task in self.background_tasks.items():
                    tasks.append(task.get_status_info())
                return {
                    "success": True,
                    "task_count": len(tasks),
                    "tasks": tasks
                }
    
    def terminate_task(self, task_id: str) -> Dict[str, Any]:
        """终止后台任务"""
        with self.task_lock:
            if task_id in self.background_tasks:
                task = self.background_tasks[task_id]
                if task.terminate():
                    logger.info(f"🛑 已终止后台任务: {task_id}")
                    return {
                        "success": True,
                        "message": f"任务 {task_id} 已终止"
                    }
                else:
                    return {
                        "success": False,
                        "error": f"任务 {task_id} 已经结束或无法终止"
                    }
            else:
                return {
                    "success": False,
                    "error": f"任务 {task_id} 不存在"
                }
    
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
    
    def _is_long_running_command(self, command: str) -> bool:
        """检查是否是可能长时间运行的命令"""
        long_running_patterns = [
            # Web服务器
            'python app.py', 'python main.py', 'python server.py',
            'flask run', 'django runserver', 'uvicorn', 'gunicorn',
            'python manage.py runserver',
            # 其他服务
            'npm start', 'yarn start', 'node server', 'node app',
            'jupyter notebook', 'jupyter lab',
            # 监控和持续任务
            'tail -f', 'watch', 'ping', 'nc -l'
        ]
        
        command_lower = command.lower()
        return any(pattern in command_lower for pattern in long_running_patterns)

    def _detect_virtual_env(self, working_dir: str) -> Optional[str]:
        """检测虚拟环境路径"""
        possible_venv_paths = [
            os.path.join(working_dir, 'venv', 'bin', 'python'),
            os.path.join(working_dir, 'env', 'bin', 'python'), 
            os.path.join(working_dir, '.venv', 'bin', 'python'),
            os.path.join(working_dir, 'virtualenv', 'bin', 'python'),
        ]
        
        for venv_python in possible_venv_paths:
            if os.path.exists(venv_python):
                logger.info(f"🐍 检测到虚拟环境: {venv_python}")
                return venv_python
        return None
    
    def _enhance_command_for_venv(self, command: str, working_dir: str) -> str:
        """为命令添加虚拟环境支持"""
        # 检测是否需要虚拟环境
        python_commands = ['python', 'pip', 'flask', 'uvicorn', 'gunicorn', 'django-admin', 'manage.py']
        if not any(cmd in command.lower() for cmd in python_commands):
            return command
            
        # 检测虚拟环境
        venv_python = self._detect_virtual_env(working_dir)
        if not venv_python:
            return command
            
        venv_dir = os.path.dirname(venv_python)
        
        # 替换python和pip命令使用虚拟环境
        enhanced_command = command
        if command.startswith('python '):
            enhanced_command = command.replace('python ', f'{venv_python} ', 1)
            logger.info(f"🔄 使用虚拟环境Python: {venv_python}")
        elif command.startswith('pip '):
            pip_path = os.path.join(venv_dir, 'pip')
            enhanced_command = command.replace('pip ', f'{pip_path} ', 1)
            logger.info(f"🔄 使用虚拟环境pip: {pip_path}")
        elif 'python' in command:
            # 对于更复杂的命令，设置虚拟环境PATH
            enhanced_command = f'export PATH="{venv_dir}:$PATH" && {command}'
            logger.info(f"🔄 设置虚拟环境PATH: {venv_dir}")
            
        return enhanced_command
    
    def _verify_service_status(self, command: str, task_id: str, working_dir: str) -> Dict[str, Any]:
        """验证服务启动状态"""
        # 检测是否是服务启动命令
        service_patterns = [
            'flask run', 'python app.py', 'python main.py', 'uvicorn', 'gunicorn', 'django'
        ]
        
        is_service_command = any(pattern in command.lower() for pattern in service_patterns)
        if not is_service_command:
            return {"verified": False, "reason": "不是服务启动命令"}
            
        # 等待服务启动
        time.sleep(3)
        
        # 从任务输出中解析实际端口
        detected_ports = self._extract_ports_from_task_output(task_id)
        
        # 如果没有从输出中解析到端口，尝试从命令中解析
        if not detected_ports:
            detected_ports = self._extract_ports_from_command(command)
        
        # 如果还是没有端口，使用默认端口
        if not detected_ports:
            if 'flask' in command.lower() or 'app.py' in command.lower():
                detected_ports = [5000, 5001, 5002]  # Flask常用端口
            elif 'uvicorn' in command.lower() or 'fastapi' in command.lower():
                detected_ports = [8000, 8001, 8002]  # FastAPI常用端口
            else:
                detected_ports = [8000, 5000, 3000]  # 通用端口
        
        logger.info(f"🔍 尝试验证服务端口: {detected_ports}")
        
        # 尝试连接每个可能的端口
        for port in detected_ports:
            verification_result = self._test_service_port(port)
            if verification_result["verified"]:
                return verification_result
                
        return {"verified": False, "reason": f"服务未在端口{detected_ports}上响应"}
    
    def _extract_ports_from_task_output(self, task_id: str) -> List[int]:
        """从任务输出中提取端口号"""
        ports = []
        try:
            with self.task_lock:
                if task_id in self.background_tasks:
                    task = self.background_tasks[task_id]
                    recent_output = task.get_recent_output(20)  # 获取最近20行输出
                    
                    # 合并stdout和stderr
                    all_output = recent_output.get('stdout', []) + recent_output.get('stderr', [])
                    
                    import re
                    for line in all_output:
                        # 匹配各种端口格式
                        port_patterns = [
                            r'Running on.*?:(\d+)',  # * Running on http://127.0.0.1:5002
                            r'localhost:(\d+)',      # localhost:5000
                            r'127\.0\.0\.1:(\d+)',   # 127.0.0.1:5000
                            r'0\.0\.0\.0:(\d+)',     # 0.0.0.0:5000
                            r'port\s+(\d+)',         # port 5000
                            r':(\d+)/',              # :5000/
                        ]
                        
                        for pattern in port_patterns:
                            matches = re.findall(pattern, line, re.IGNORECASE)
                            for match in matches:
                                port = int(match)
                                if 1000 <= port <= 65535 and port not in ports:  # 有效端口范围
                                    ports.append(port)
                                    logger.info(f"🎯 从输出中解析到端口: {port} (来源: {line.strip()[:50]}...)")
        except Exception as e:
            logger.debug(f"解析任务输出端口时出错: {e}")
            
        return ports
    
    def _extract_ports_from_command(self, command: str) -> List[int]:
        """从命令中提取端口号"""
        ports = []
        try:
            import re
            # 匹配命令中的端口参数
            port_patterns = [
                r'--port[=\s]+(\d+)',     # --port=5000 或 --port 5000
                r'-p[=\s]+(\d+)',         # -p=5000 或 -p 5000
                r'port[=\s]+(\d+)',       # port=5000
                r':(\d+)\s*$',            # 命令末尾的 :5000
            ]
            
            for pattern in port_patterns:
                matches = re.findall(pattern, command, re.IGNORECASE)
                for match in matches:
                    port = int(match)
                    if 1000 <= port <= 65535 and port not in ports:
                        ports.append(port)
                        logger.info(f"🎯 从命令中解析到端口: {port}")
        except Exception as e:
            logger.debug(f"解析命令端口时出错: {e}")
            
        return ports
    
    def _test_service_port(self, port: int) -> Dict[str, Any]:
        """测试特定端口的服务"""
        test_urls = [
            f"http://localhost:{port}",
            f"http://127.0.0.1:{port}",
            f"http://localhost:{port}/health",
            f"http://localhost:{port}/api/health"
        ]
        
        for url in test_urls:
            try:
                result = subprocess.run(
                    ['curl', '-s', '-o', '/dev/null', '-w', '%{http_code}', url],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0 and result.stdout.strip() in ['200', '404', '405']:
                    logger.info(f"✅ 服务验证成功: {url} (HTTP {result.stdout.strip()})")
                    return {
                        "verified": True, 
                        "url": url, 
                        "status_code": result.stdout.strip(),
                        "port": port
                    }
            except Exception as e:
                logger.debug(f"🔍 测试 {url} 失败: {e}")
                continue
                
        # 检查端口是否被占用
        try:
            result = subprocess.run(
                ['lsof', '-i', f':{port}'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                logger.warning(f"⚠️ 端口 {port} 已被占用，但HTTP请求失败")
                return {"verified": False, "reason": f"端口{port}被占用但服务不响应"}
        except Exception:
            pass
            
        return {"verified": False, "reason": f"端口{port}不响应"}

    def execute_command(self, command: str, working_dir: Optional[str] = None, force_background: bool = None) -> Dict[str, Any]:
        """
        执行命令并返回结果
        
        Args:
            command: 要执行的命令
            working_dir: 工作目录
            force_background: 强制后台执行，None=自动判断
            
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
        
        # 检查是否是长时间运行的命令
        is_long_running = self._is_long_running_command(command)
        
        # 决定执行方式
        should_run_background = force_background
        if should_run_background is None:
            should_run_background = is_long_running
        
        if should_run_background:
            logger.info(f"🔄 命令将在后台执行: {command}")
            bg_result = self.execute_command_background(command, working_dir)
            if bg_result["success"]:
                # 等待一小段时间收集初始输出
                time.sleep(2)
                task_status = self.get_task_status(bg_result["task_id"])
                recent_output = task_status.get("recent_output", {})
                
                # 验证服务状态（如果是服务命令）
                verification = self._verify_service_status(command, bg_result["task_id"], working_dir or os.getcwd())
                verification_info = ""
                if verification["verified"]:
                    verification_info = f"\n\n🎉 服务验证成功!\n✅ 服务地址: {verification['url']}\n📊 HTTP状态: {verification['status_code']}"
                elif verification["reason"] != "不是服务启动命令":
                    verification_info = f"\n\n⚠️ 服务验证失败: {verification['reason']}"
                
                return {
                    "success": True,
                    "output": f"任务已在后台启动\n任务ID: {bg_result['task_id']}\nPID: {bg_result['pid']}\n\n初始输出:\n" + 
                             '\n'.join(recent_output.get('stdout', [])) + verification_info,
                    "error": '\n'.join(recent_output.get('stderr', [])),
                    "return_code": 0,
                    "command": command,
                    "working_dir": bg_result["working_dir"],
                    "execution_time": 2.0,
                    "background": True,
                    "task_id": bg_result["task_id"],
                    "verification": verification
                }
            else:
                return {
                    "success": False,
                    "error": bg_result["error"],
                    "output": "",
                    "return_code": -1
                }
        
        try:
            # 前台执行
            cwd = working_dir or os.getcwd()
            logger.info(f"执行环境: {cwd}")
            
            # 增强命令以支持虚拟环境
            enhanced_command = self._enhance_command_for_venv(command, cwd)
            if enhanced_command != command:
                logger.info(f"🔄 命令已增强虚拟环境支持")
            
            timeout = 10 if is_long_running else 30  # 长时间运行的命令使用较短超时
            
            if is_long_running:
                logger.warning(f"检测到可能长时间运行的命令，使用 {timeout} 秒超时: {enhanced_command}")
            
            # 执行命令
            logger.info(f"开始执行命令 (超时: {timeout}s)...")
            start_time = __import__('time').time()
            
            result = subprocess.run(
                enhanced_command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=cwd,
                timeout=timeout
            )
            
            execution_time = __import__('time').time() - start_time
            logger.info(f"命令执行完成，耗时: {execution_time:.2f}s")
            
            # 详细记录执行结果
            if result.returncode == 0:
                logger.info(f"✅ 命令执行成功，返回码: {result.returncode}")
                if result.stdout:
                    logger.info(f"📤 标准输出 ({len(result.stdout)} 字符):")
                    # 显示输出内容的前几行
                    output_lines = result.stdout.strip().split('\n')
                    for i, line in enumerate(output_lines[:5]):  # 最多显示前5行
                        logger.info(f"  │ {line}")
                    if len(output_lines) > 5:
                        logger.info(f"  │ ... ({len(output_lines)-5} 行更多内容)")
                else:
                    logger.info("📤 无标准输出")
            else:
                logger.warning(f"❌ 命令执行失败，返回码: {result.returncode}")
                if result.stderr:
                    logger.warning(f"📥 错误输出:")
                    error_lines = result.stderr.strip().split('\n')
                    for line in error_lines[:3]:  # 显示前3行错误
                        logger.warning(f"  │ {line}")
                if result.stdout:
                    logger.info(f"📤 标准输出:")
                    output_lines = result.stdout.strip().split('\n')
                    for line in output_lines[:3]:  # 显示前3行输出
                        logger.info(f"  │ {line}")
            
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr,
                "return_code": result.returncode,
                "command": command,
                "working_dir": cwd,
                "execution_time": execution_time
            }
            
        except subprocess.TimeoutExpired:
            execution_time = __import__('time').time() - start_time
            if is_long_running:
                logger.warning(f"⏰ 长时间运行命令超时 ({timeout}s)，可能正在后台运行: {command}")
                return {
                    "success": True,  # 对于服务类命令，超时可能是正常的
                    "output": f"命令可能正在后台运行 (超时 {timeout}s)",
                    "error": f"命令在 {timeout} 秒后超时，但可能仍在运行",
                    "return_code": 0,
                    "command": command,
                    "working_dir": cwd,
                    "execution_time": execution_time,
                    "timeout": True
                }
            else:
                logger.error(f"❌ 命令执行超时 ({timeout}s): {command}")
                return {
                    "success": False,
                    "error": f"命令执行超时 ({timeout}s)",
                    "output": "",
                    "return_code": -1,
                    "command": command,
                    "working_dir": cwd,
                    "execution_time": execution_time
                }
        except Exception as e:
            logger.error(f"❌ 执行命令时发生异常: {str(e)}")
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
    
    # 构建详细的执行结果报告
    execution_time = result.get('execution_time', 0)
    timeout_info = ""
    if result.get('timeout'):
        timeout_info = f"\n⏰ 注意：命令可能仍在后台运行"
    
    if result["success"]:
        logger.info(f"[Tool] 命令执行成功 (耗时: {execution_time:.2f}s)")
        
        # 构建输出信息
        output_info = ""
        if result['output']:
            output_lines = result['output'].strip().split('\n')
            if len(output_lines) <= 10:
                output_info = f"\n📤 输出内容:\n{result['output']}"
            else:
                # 如果输出太长，显示前5行和后3行
                first_lines = '\n'.join(output_lines[:5])
                last_lines = '\n'.join(output_lines[-3:])
                output_info = f"\n📤 输出内容 (共{len(output_lines)}行):\n{first_lines}\n... ({len(output_lines)-8} 行省略) ...\n{last_lines}"
        else:
            output_info = "\n📤 无输出内容"
        
        return f"{warning_info}✅ 命令执行成功 (耗时: {execution_time:.2f}s){output_info}{timeout_info}\n\n返回码: {result['return_code']}"
    else:
        logger.warning(f"[Tool] 命令执行失败: {result['error']}")
        
        # 构建错误信息
        error_info = ""
        if result['error']:
            error_info = f"\n📥 错误信息:\n{result['error']}"
        
        output_info = ""
        if result['output']:
            output_info = f"\n📤 输出内容:\n{result['output']}"
        
        return f"{warning_info}❌ 命令执行失败 (耗时: {execution_time:.2f}s){error_info}{output_info}\n\n返回码: {result['return_code']}"


@tool
def execute_command_background(command: str, working_directory: str = None) -> str:
    """
    在后台执行长时间运行的命令（如服务器、监控工具等）
    
    Args:
        command: 要执行的命令
        working_directory: 工作目录路径（可选）
    
    Returns:
        后台任务启动结果和任务ID
    """
    logger.info(f"[Tool] 后台执行命令: {command}")
    
    result = terminal_executor.execute_command_background(command, working_directory)
    
    if result["success"]:
        logger.info(f"[Tool] 后台任务启动成功: {result['task_id']}")
        return f"✅ 后台任务启动成功!\n任务ID: {result['task_id']}\nPID: {result['pid']}\n命令: {result['command']}\n工作目录: {result['working_dir']}\n\n{result['message']}"
    else:
        logger.error(f"[Tool] 后台任务启动失败: {result['error']}")
        return f"❌ 后台任务启动失败:\n{result['error']}"


@tool
def get_background_tasks_status(task_id: str = None) -> str:
    """
    获取后台任务状态
    
    Args:
        task_id: 特定任务ID，不提供则返回所有任务状态
    
    Returns:
        任务状态信息
    """
    logger.info(f"[Tool] 查询后台任务状态: {task_id or '全部'}")
    
    result = terminal_executor.get_task_status(task_id)
    
    if not result["success"]:
        return f"❌ 查询失败: {result['error']}"
    
    if task_id:
        # 单个任务详情
        task = result["task"]
        recent_output = result["recent_output"]
        
        status_emoji = {
            "running": "🟢",
            "completed": "✅", 
            "failed": "❌",
            "terminated": "🛑"
        }.get(task["status"], "❓")
        
        output_info = ""
        if recent_output["stdout"]:
            output_info += f"\n📤 最近输出:\n" + '\n'.join(recent_output["stdout"][-5:])
        if recent_output["stderr"]:
            output_info += f"\n📥 错误输出:\n" + '\n'.join(recent_output["stderr"][-3:])
        
        return f"""🔍 任务详情:
{status_emoji} 状态: {task['status']}
🆔 任务ID: {task['task_id']}
💻 命令: {task['command']}
📂 工作目录: {task['working_dir']}
⏰ 开始时间: {task['start_time']}
🕐 运行时长: {task['runtime_seconds']:.1f}秒
📊 输出行数: {task['output_lines']} (标准) / {task['error_lines']} (错误)
🆔 进程ID: {task['pid']}{output_info}"""
    else:
        # 所有任务概览
        tasks = result["tasks"]
        if not tasks:
            return "📋 当前没有后台任务运行"
        
        summary = f"📋 后台任务概览 (共 {result['task_count']} 个):\n"
        summary += "=" * 50 + "\n"
        
        for task in tasks:
            status_emoji = {
                "running": "🟢",
                "completed": "✅", 
                "failed": "❌",
                "terminated": "🛑"
            }.get(task["status"], "❓")
            
            summary += f"{status_emoji} [{task['task_id']}] {task['command'][:40]}{'...' if len(task['command']) > 40 else ''}\n"
            summary += f"   ⏱️  运行时长: {task['runtime_seconds']:.1f}s | 📊 输出: {task['output_lines']}行\n\n"
        
        return summary


@tool
def terminate_background_task(task_id: str) -> str:
    """
    终止指定的后台任务
    
    Args:
        task_id: 要终止的任务ID
    
    Returns:
        终止操作结果
    """
    logger.info(f"[Tool] 终止后台任务: {task_id}")
    
    result = terminal_executor.terminate_task(task_id)
    
    if result["success"]:
        logger.info(f"[Tool] 后台任务终止成功: {task_id}")
        return f"✅ {result['message']}"
    else:
        logger.warning(f"[Tool] 后台任务终止失败: {result['error']}")
        return f"❌ 终止失败: {result['error']}"


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