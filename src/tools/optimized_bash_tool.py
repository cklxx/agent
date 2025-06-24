# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT

"""
优化的Bash工具 - 改进的进程管理、资源清理和错误处理
"""

import os
import subprocess
import logging
import time
import tempfile
import threading
import json
import signal

try:
    import psutil

    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
from typing import Optional, Dict, Any, List
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum

from .middleware import (
    get_tool_middleware,
    ToolError,
    ToolTimeoutError,
    ToolSecurityError,
)

logger = logging.getLogger(__name__)


class ProcessStatus(Enum):
    """进程状态枚举"""

    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"


@dataclass
class ProcessInfo:
    """进程信息数据类"""

    pid: int
    command: str
    working_dir: str
    log_file: str
    start_time: float
    status: ProcessStatus = ProcessStatus.STARTING
    auto_cleanup: bool = True
    resource_usage: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "pid": self.pid,
            "command": self.command,
            "working_dir": self.working_dir,
            "log_file": self.log_file,
            "start_time": self.start_time,
            "status": self.status.value,
            "auto_cleanup": self.auto_cleanup,
            "resource_usage": self.resource_usage,
        }


class OptimizedProcessManager:
    """优化的进程管理器"""

    def __init__(self, processes_file: Optional[str] = None):
        self.processes_file = processes_file or "/tmp/optimized_agent_processes.json"
        self._processes: Dict[str, ProcessInfo] = {}
        self._lock = threading.RLock()
        self._monitor_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()

        # 启动进程监控线程
        self._start_monitor()

        # 加载现有进程
        self._load_processes()

    def _start_monitor(self):
        """启动进程监控线程"""
        if self._monitor_thread is None or not self._monitor_thread.is_alive():
            self._monitor_thread = threading.Thread(
                target=self._monitor_processes, daemon=True, name="ProcessMonitor"
            )
            self._monitor_thread.start()

    def _monitor_processes(self):
        """监控进程状态"""
        while not self._shutdown_event.is_set():
            try:
                with self._lock:
                    for process_id, process_info in list(self._processes.items()):
                        if self._is_process_running(process_info.pid):
                            # 更新资源使用情况
                            self._update_resource_usage(process_info)
                            process_info.status = ProcessStatus.RUNNING
                        else:
                            # 进程已停止
                            if process_info.status == ProcessStatus.RUNNING:
                                logger.info(
                                    f"进程 {process_id} (PID: {process_info.pid}) 已停止"
                                )
                                process_info.status = ProcessStatus.STOPPED

                            # 自动清理已停止的进程
                            if (
                                process_info.auto_cleanup
                                and process_info.status == ProcessStatus.STOPPED
                            ):
                                self._cleanup_process_resources(
                                    process_id, process_info
                                )
                                del self._processes[process_id]

                # 保存进程状态
                self._save_processes()

            except Exception as e:
                logger.error(f"进程监控出错: {e}")

            # 等待下一次检查
            self._shutdown_event.wait(5)  # 每5秒检查一次

    def _is_process_running(self, pid: int) -> bool:
        """检查进程是否运行"""
        if HAS_PSUTIL:
            try:
                return psutil.pid_exists(pid)
            except Exception:
                pass

        # 备用方法
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    def _update_resource_usage(self, process_info: ProcessInfo):
        """更新进程资源使用情况"""
        if not HAS_PSUTIL:
            process_info.resource_usage = {"status": "psutil_not_available"}
            return

        try:
            process = psutil.Process(process_info.pid)
            process_info.resource_usage = {
                "cpu_percent": process.cpu_percent(),
                "memory_info": process.memory_info()._asdict(),
                "create_time": process.create_time(),
                "status": process.status(),
                "num_threads": process.num_threads(),
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            process_info.resource_usage = {}

    def _cleanup_process_resources(self, process_id: str, process_info: ProcessInfo):
        """清理进程资源"""
        try:
            # 删除日志文件
            if os.path.exists(process_info.log_file):
                os.remove(process_info.log_file)
                logger.debug(
                    f"删除进程 {process_id} 的日志文件: {process_info.log_file}"
                )
        except Exception as e:
            logger.warning(f"清理进程 {process_id} 资源失败: {e}")

    def _load_processes(self):
        """加载进程信息"""
        if not os.path.exists(self.processes_file):
            return

        try:
            with open(self.processes_file, "r") as f:
                data = json.load(f)

            with self._lock:
                for process_id, process_data in data.items():
                    try:
                        process_info = ProcessInfo(
                            pid=process_data["pid"],
                            command=process_data["command"],
                            working_dir=process_data["working_dir"],
                            log_file=process_data["log_file"],
                            start_time=process_data["start_time"],
                            status=ProcessStatus(process_data.get("status", "running")),
                            auto_cleanup=process_data.get("auto_cleanup", True),
                            resource_usage=process_data.get("resource_usage", {}),
                        )

                        # 检查进程是否仍在运行
                        if self._is_process_running(process_info.pid):
                            self._processes[process_id] = process_info
                        elif process_info.auto_cleanup:
                            # 清理已停止的自动清理进程
                            self._cleanup_process_resources(process_id, process_info)

                    except Exception as e:
                        logger.warning(f"加载进程 {process_id} 信息失败: {e}")

        except Exception as e:
            logger.error(f"加载进程文件失败: {e}")

    def _save_processes(self):
        """保存进程信息"""
        try:
            data = {}
            with self._lock:
                for process_id, process_info in self._processes.items():
                    data[process_id] = process_info.to_dict()

            with open(self.processes_file, "w") as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.error(f"保存进程文件失败: {e}")

    def register_process(
        self,
        pid: int,
        command: str,
        working_dir: str,
        log_file: str,
        auto_cleanup: bool = True,
    ) -> str:
        """注册进程"""
        process_id = f"proc_{int(time.time())}_{pid}"

        process_info = ProcessInfo(
            pid=pid,
            command=command,
            working_dir=working_dir,
            log_file=log_file,
            start_time=time.time(),
            auto_cleanup=auto_cleanup,
        )

        with self._lock:
            self._processes[process_id] = process_info

        self._save_processes()
        logger.info(f"注册进程 {process_id} (PID: {pid})")
        return process_id

    def get_process_info(self, process_id: str) -> Optional[ProcessInfo]:
        """获取进程信息"""
        with self._lock:
            return self._processes.get(process_id)

    def list_processes(self) -> Dict[str, ProcessInfo]:
        """列出所有进程"""
        with self._lock:
            return self._processes.copy()

    def stop_process(self, process_id: str, force: bool = False) -> bool:
        """停止进程"""
        with self._lock:
            process_info = self._processes.get(process_id)
            if not process_info:
                return False

            try:
                process_info.status = ProcessStatus.STOPPING

                if force:
                    # 强制终止
                    os.kill(process_info.pid, signal.SIGKILL)
                else:
                    # 优雅终止
                    os.kill(process_info.pid, signal.SIGTERM)

                    # 等待进程终止
                    for _ in range(10):  # 最多等待10秒
                        if not self._is_process_running(process_info.pid):
                            break
                        time.sleep(1)

                    # 如果仍在运行，强制终止
                    if self._is_process_running(process_info.pid):
                        os.kill(process_info.pid, signal.SIGKILL)

                process_info.status = ProcessStatus.STOPPED
                logger.info(f"停止进程 {process_id} (PID: {process_info.pid})")
                return True

            except OSError as e:
                if e.errno == 3:  # No such process
                    process_info.status = ProcessStatus.STOPPED
                    return True
                else:
                    logger.error(f"停止进程 {process_id} 失败: {e}")
                    process_info.status = ProcessStatus.FAILED
                    return False

    def cleanup_all(self):
        """清理所有进程"""
        with self._lock:
            for process_id in list(self._processes.keys()):
                self.stop_process(process_id, force=True)

        # 停止监控线程
        self._shutdown_event.set()
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5)


# 全局进程管理器
_global_process_manager: Optional[OptimizedProcessManager] = None
_manager_lock = threading.Lock()


def get_process_manager() -> OptimizedProcessManager:
    """获取全局进程管理器"""
    global _global_process_manager

    if _global_process_manager is None:
        with _manager_lock:
            if _global_process_manager is None:
                _global_process_manager = OptimizedProcessManager()

    return _global_process_manager


class OptimizedBashTool:
    """优化的Bash工具"""

    # 安全检查
    BANNED_COMMANDS = {
        "curl",
        "wget",
        "telnet",
        "nc",
        "ssh",
        "scp",
        "ftp",
        "sftp",
        "rm -rf",
        "mkfs",
        "dd",
        "format",
        "chmod 777",
    }

    DISCOURAGED_COMMANDS = {
        "find": "Use optimized_glob_search instead",
        "grep": "Use optimized_grep_search instead",
        "cat": "Use optimized_view_file instead",
        "head": "Use optimized_view_file instead",
        "tail": "Use optimized_view_file instead",
        "ls": "Use optimized_list_files instead",
    }

    def __init__(self):
        self.process_manager = get_process_manager()

    def _check_command_security(self, command: str) -> None:
        """检查命令安全性"""
        import shlex

        try:
            # 解析命令以获取实际的命令名称
            tokens = shlex.split(command)
            if not tokens:
                return

            # 获取第一个token作为命令名（可能包含路径）
            cmd_name = tokens[0].split("/")[-1]  # 移除路径前缀

            # 检查禁止的命令
            for banned in self.BANNED_COMMANDS:
                if " " in banned:
                    # 带参数的禁止命令，检查完整的命令行
                    if banned in command:
                        raise ToolSecurityError(
                            f"Command '{banned}' is banned for security reasons"
                        )
                else:
                    # 单个命令名称
                    if cmd_name == banned:
                        raise ToolSecurityError(
                            f"Command '{banned}' is banned for security reasons"
                        )

            # 检查不推荐的命令
            for discouraged, suggestion in self.DISCOURAGED_COMMANDS.items():
                if cmd_name == discouraged or cmd_name.startswith(discouraged + " "):
                    logger.warning(
                        f"Command '{discouraged}' is discouraged. {suggestion}"
                    )

        except ValueError:
            # 如果解析失败，使用原来的简单检查
            for banned in self.BANNED_COMMANDS:
                if " " in banned:
                    # 带参数的禁止命令
                    if banned in command:
                        raise ToolSecurityError(
                            f"Command '{banned}' is banned for security reasons"
                        )
                else:
                    # 单个命令
                    if (
                        command.strip().startswith(banned + " ")
                        or command.strip() == banned
                    ):
                        raise ToolSecurityError(
                            f"Command '{banned}' is banned for security reasons"
                        )

    def execute_foreground(
        self,
        command: str,
        working_directory: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> str:
        """执行前台命令"""
        # 安全检查
        self._check_command_security(command)

        # 设置默认超时
        if timeout is None:
            timeout = 120000  # 2分钟

        timeout_seconds = timeout / 1000.0

        logger.info(f"执行前台命令: {command}")

        try:
            # 创建进程
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=working_directory,
                bufsize=1,
                universal_newlines=True,
            )

            output_lines = []
            start_time = time.time()

            # 实时读取输出
            while True:
                # 检查超时
                if time.time() - start_time > timeout_seconds:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                    raise ToolTimeoutError(
                        f"Command timed out after {timeout_seconds}s"
                    )

                # 检查进程状态
                if process.poll() is not None:
                    # 读取剩余输出
                    remaining = process.stdout.read()
                    if remaining:
                        output_lines.append(remaining)
                    break

                # 读取输出行
                try:
                    line = process.stdout.readline()
                    if line:
                        output_lines.append(line)
                        logger.debug(f"Command output: {line.rstrip()}")
                except Exception:
                    time.sleep(0.1)

            # 获取退出码
            return_code = process.wait()
            output = "".join(output_lines)

            # 限制输出长度
            if len(output) > 30000:
                output = output[:30000] + "\n... (output truncated)"

            # 添加执行信息
            execution_time = time.time() - start_time
            output += f"\n\nExit code: {return_code}"
            output += f"\nExecution time: {execution_time:.2f}s"

            if return_code != 0:
                logger.warning(f"Command failed with exit code {return_code}")

            return output

        except subprocess.TimeoutExpired:
            raise ToolTimeoutError(f"Command timed out after {timeout_seconds}s")
        except Exception as e:
            raise ToolError(f"Command execution failed: {str(e)}")

    def execute_background(
        self,
        command: str,
        working_directory: Optional[str] = None,
        auto_cleanup: bool = True,
    ) -> str:
        """执行后台命令"""
        # 安全检查
        self._check_command_security(command)

        logger.info(f"执行后台命令: {command}")

        try:
            # 创建日志文件
            log_file = tempfile.NamedTemporaryFile(delete=False, suffix=".log")
            log_path = log_file.name
            log_file.close()

            # 启动进程
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=open(log_path, "w"),
                stderr=subprocess.STDOUT,
                cwd=working_directory,
            )

            # 注册进程
            process_id = self.process_manager.register_process(
                pid=process.pid,
                command=command,
                working_dir=working_directory or os.getcwd(),
                log_file=log_path,
                auto_cleanup=auto_cleanup,
            )

            result = f"Started background process: {process_id}\n"
            result += f"PID: {process.pid}\n"
            result += f"Log file: {log_path}\n"
            result += f"Working directory: {working_directory or os.getcwd()}\n"
            result += f"Auto cleanup: {auto_cleanup}"

            if auto_cleanup:
                result += (
                    "\nNote: Process will be automatically cleaned up when stopped"
                )

            return result

        except Exception as e:
            raise ToolError(f"Background command execution failed: {str(e)}")

    def list_background_processes(self) -> str:
        """列出后台进程"""
        processes = self.process_manager.list_processes()

        if not processes:
            return "No background processes currently running"

        result = f"Background Processes ({len(processes)} total):\n"
        result += "=" * 60 + "\n"

        for process_id, process_info in processes.items():
            result += f"\nProcess ID: {process_id}\n"
            result += f"  PID: {process_info.pid}\n"
            result += f"  Status: {process_info.status.value}\n"
            result += f"  Command: {process_info.command}\n"
            result += f"  Working Dir: {process_info.working_dir}\n"
            result += f"  Started: {time.ctime(process_info.start_time)}\n"
            result += f"  Auto Cleanup: {process_info.auto_cleanup}\n"
            result += f"  Log File: {process_info.log_file}\n"

            # 显示资源使用情况
            if process_info.resource_usage:
                usage = process_info.resource_usage
                result += f"  CPU: {usage.get('cpu_percent', 0):.1f}%\n"
                memory = usage.get("memory_info", {})
                if memory:
                    result += f"  Memory: {memory.get('rss', 0) / 1024 / 1024:.1f} MB\n"

            result += "-" * 40 + "\n"

        return result

    def stop_background_process(self, process_id: str, force: bool = False) -> str:
        """停止后台进程"""
        if self.process_manager.stop_process(process_id, force):
            action = "force killed" if force else "stopped"
            return f"Process {process_id} has been {action}"
        else:
            return f"Failed to stop process {process_id} or process not found"

    def get_process_logs(self, process_id: str, lines: int = 50) -> str:
        """获取进程日志"""
        process_info = self.process_manager.get_process_info(process_id)
        if not process_info:
            return f"Process {process_id} not found"

        log_file = process_info.log_file
        if not os.path.exists(log_file):
            return f"Log file not found: {log_file}"

        try:
            # 读取最后N行
            result = subprocess.run(
                f"tail -{lines} {log_file}", shell=True, capture_output=True, text=True
            )

            if result.returncode == 0:
                output = f"Logs for process {process_id} (last {lines} lines):\n"
                output += "=" * 50 + "\n"
                output += result.stdout
                return output
            else:
                return f"Failed to read log file: {result.stderr}"

        except Exception as e:
            return f"Error reading logs: {str(e)}"


# 工具函数
def optimized_bash_command(
    command: str,
    timeout: Optional[int] = None,
    working_directory: Optional[str] = None,
    run_in_background: bool = False,
) -> str:
    """
    优化的bash命令执行工具

    Args:
        command: shell命令
        timeout: 超时时间（毫秒）
        working_directory: 工作目录
        run_in_background: 是否后台运行

    Returns:
        命令执行结果
    """
    bash_tool = OptimizedBashTool()

    if run_in_background:
        return bash_tool.execute_background(command, working_directory)
    else:
        return bash_tool.execute_foreground(command, working_directory, timeout)


def list_background_processes() -> str:
    """列出后台进程"""
    bash_tool = OptimizedBashTool()
    return bash_tool.list_background_processes()


def stop_background_process(process_id: str, force: bool = False) -> str:
    """停止后台进程"""
    bash_tool = OptimizedBashTool()
    return bash_tool.stop_background_process(process_id, force)


def get_process_logs(process_id: str, lines: int = 50) -> str:
    """获取进程日志"""
    bash_tool = OptimizedBashTool()
    return bash_tool.get_process_logs(process_id, lines)


def cleanup_all_processes():
    """清理所有进程"""
    manager = get_process_manager()
    manager.cleanup_all()


# 导出工具
__all__ = [
    "optimized_bash_command",
    "list_background_processes",
    "stop_background_process",
    "get_process_logs",
    "cleanup_all_processes",
    "OptimizedBashTool",
    "OptimizedProcessManager",
]
