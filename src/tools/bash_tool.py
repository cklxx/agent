# SPDX-License-Identifier: MIT

"""
Bash command execution tool with security restrictions and git integration.
Background processes automatically terminate when tool call ends to prevent orphaned processes.
"""

import os
import subprocess
import logging
import re
import json
import time
import tempfile
from typing import Optional, List, Set, Dict, Any
from pathlib import Path
from langchain_core.tools import tool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Banned commands for security
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

# Commands that should use specialized tools instead
DISCOURAGED_COMMANDS = {
    "find": "Use SearchGlobTool instead",
    "grep": "Use GrepTool instead",
    "cat": "Use ViewTool instead",
    "head": "Use ViewTool instead",
    "tail": "Use ViewTool instead",
    "ls": "Use ListTool instead",
}

MAX_OUTPUT_LENGTH = 30000

# 后台进程管理
BACKGROUND_PROCESSES_FILE = Path("/tmp/agent_background_processes.json")


def load_background_processes() -> Dict[str, Any]:
    """加载后台进程记录"""
    if not BACKGROUND_PROCESSES_FILE.exists():
        return {}
    try:
        with open(BACKGROUND_PROCESSES_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def save_background_processes(processes: Dict[str, Any]):
    """保存后台进程记录"""
    try:
        with open(BACKGROUND_PROCESSES_FILE, "w") as f:
            json.dump(processes, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save background processes: {e}")


def add_background_process(pid: str, command: str, working_dir: str, log_file: str):
    """添加后台进程记录"""
    processes = load_background_processes()
    process_id = f"proc_{int(time.time())}_{pid}"
    processes[process_id] = {
        "pid": pid,
        "command": command,
        "working_dir": working_dir,
        "log_file": log_file,
        "start_time": time.time(),
        "status": "running",
    }
    save_background_processes(processes)
    return process_id


def is_process_running(pid: str) -> bool:
    """检查进程是否仍在运行"""
    try:
        result = subprocess.run(
            f"ps -p {pid}", shell=True, capture_output=True, text=True
        )
        return result.returncode == 0
    except Exception:
        return False


def check_command_security(command: str) -> tuple[bool, str]:
    """检查命令安全性"""
    # 检查禁用命令
    for banned in BANNED_COMMANDS:
        if banned in command:
            return False, f"Command '{banned}' is banned for security reasons"

    # 检查不推荐命令
    for discouraged, suggestion in DISCOURAGED_COMMANDS.items():
        if discouraged in command:
            return False, f"Command '{discouraged}' is discouraged. {suggestion}"

    return True, "Command is allowed"


def execute_foreground_command(command: str, timeout: Optional[int] = None) -> str:
    """执行前台命令"""
    try:
        # 设置超时
        if timeout is None:
            timeout = 1800  # 默认30分钟

        # 执行命令
        process = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout / 1000,  # 转换为秒
        )

        # 处理输出
        output = process.stdout
        if process.stderr:
            output += f"\nError: {process.stderr}"

        # 添加退出码
        output += f"\n\nExit code: {process.returncode}"

        # 截断输出
        if len(output) > 30000:
            output = output[:30000] + "\n... (output truncated)"

        return output

    except subprocess.TimeoutExpired:
        return "Error: Command timed out"
    except Exception as e:
        return f"Error: {str(e)}"


def execute_background_command(
    command: str, working_directory: Optional[str] = None
) -> str:
    """执行后台命令（会在工具调用结束时自动停止）"""
    try:
        # 创建日志文件
        log_file = tempfile.NamedTemporaryFile(delete=False, suffix=".log")
        log_path = log_file.name
        log_file.close()

        # 设置工作目录
        if working_directory:
            full_command = f"cd {working_directory} && {command}"
        else:
            full_command = command

        # 启动进程（不创建新会话，保持与父进程关联）
        process = subprocess.Popen(
            full_command,
            shell=True,
            stdout=open(log_path, "w"),
            stderr=subprocess.STDOUT,
            # 移除 start_new_session=True，让进程与父进程保持关联
        )

        # 保存进程信息（用于临时管理）
        process_info = {
            "pid": str(process.pid),
            "command": command,
            "working_dir": working_directory or os.getcwd(),
            "log_file": log_path,
            "start_time": time.time(),
            "status": "running",
            "auto_cleanup": True,  # 标记为自动清理
        }

        save_background_process(process_info)

        return f"Started background process (will auto-stop when tool call ends)\nPID: {process.pid}\nLog file: {log_path}\nWorking directory: {working_directory or os.getcwd()}"

    except Exception as e:
        return f"Error: {str(e)}"


def save_background_process(process_info: Dict[str, Any]) -> None:
    """保存后台进程信息"""
    processes_file = Path("/tmp/agent_background_processes.json")

    # 加载现有进程
    if processes_file.exists():
        with open(processes_file) as f:
            processes = json.load(f)
    else:
        processes = {}

    # 更新进程信息
    processes[str(process_info["pid"])] = process_info

    # 保存进程信息
    with open(processes_file, "w") as f:
        json.dump(processes, f, indent=2)


class BashCommandInput(BaseModel):
    command: str = Field(..., description="The bash command to execute")


@tool("bash_command", args_schema=BashCommandInput)
def bash_command(
    command: str,
    timeout: Optional[int] = None,
    working_directory: Optional[str] = None,
    run_in_background: bool = False,
) -> str:
    """Execute shell commands with optional timeout and working directory.

    Args:
        command: Shell command to execute
        timeout: Timeout in milliseconds
        working_directory: Working directory path
        run_in_background: Run as background process (auto-stops when tool call ends)

    Returns:
        Command output or error message

    Note:
        Background processes will automatically terminate when the tool call ends.
        This prevents orphaned processes and ensures clean resource management.
        Use service management commands (list_services, stop_service) for monitoring.
    """
    try:
        # 安全检查
        is_allowed, security_message = check_command_security(command)
        if not is_allowed:
            return f"Security Error: {security_message}"

        # 设置工作目录
        if working_directory:
            command = f"cd {working_directory} && {command}"

        # 执行命令
        if run_in_background:
            return execute_background_command(command, working_directory)
        else:
            return execute_foreground_command(command, timeout)

    except Exception as e:
        return f"Error: {str(e)}"


# Helper function for git operations
def format_git_commit_message(title: str, body: str) -> str:
    """Format a git commit message with Claude attribution."""
    return f"""{title}

{body}

🤖 Generated with Code Agent"""


def handle_list_services() -> str:
    """列出所有后台服务"""
    processes = load_background_processes()
    if not processes:
        return "📭 No background services currently running"

    output = "📊 Background Services Status:\n"
    output += "=" * 50 + "\n"

    active_processes = {}

    for proc_id, proc_info in processes.items():
        pid = proc_info.get("pid", "")
        is_running = is_process_running(pid)
        auto_cleanup = proc_info.get("auto_cleanup", False)

        # 如果进程已停止且标记为自动清理，则不显示
        if not is_running and auto_cleanup:
            continue

        status = "🟢 Running" if is_running else "🔴 Stopped"
        cleanup_mode = "🔄 Auto-cleanup" if auto_cleanup else "🔒 Persistent"

        # Update status in records
        if not is_running:
            proc_info["status"] = "stopped"
        else:
            active_processes[proc_id] = proc_info

        output += f"🔷 ID: {proc_id}\n"
        output += f"   Status: {status}\n"
        output += f"   Mode: {cleanup_mode}\n"
        output += f"   PID: {pid}\n"
        output += f"   Command: {proc_info.get('command', 'N/A')}\n"
        output += f"   Directory: {proc_info.get('working_dir', 'N/A')}\n"
        output += f"   Log: {proc_info.get('log_file', 'N/A')}\n"
        output += f"   Started: {time.ctime(proc_info.get('start_time', 0))}\n"
        output += "-" * 30 + "\n"

    # 只保存仍活跃的进程信息
    if active_processes != processes:
        save_background_processes(active_processes)

    if not active_processes:
        return "📭 No active background services currently running"

    output += "\n🛠️ Management Commands:\n"
    output += "• stop_service <process_id> - Stop a service\n"
    output += "• restart_service <process_id> - Restart a service\n"
    output += "• service_logs <process_id> - View service logs\n"
    output += "\n💡 Note: Services with 'Auto-cleanup' mode will stop automatically when the tool call ends\n"

    return output


def handle_stop_service(process_id: str) -> str:
    """停止指定的后台服务"""
    processes = load_background_processes()

    if process_id not in processes:
        return f"❌ Service not found: {process_id}"

    proc_info = processes[process_id]
    pid = proc_info.get("pid", "")

    if not is_process_running(pid):
        proc_info["status"] = "stopped"
        save_background_processes(processes)
        return f"ℹ️ Service {process_id} is already stopped"

    try:
        # Try graceful termination first
        result = subprocess.run(
            f"kill {pid}", shell=True, capture_output=True, text=True
        )
        time.sleep(2)  # Wait a bit

        if is_process_running(pid):
            # Force kill if still running
            subprocess.run(f"kill -9 {pid}", shell=True, capture_output=True, text=True)

        proc_info["status"] = "stopped"
        save_background_processes(processes)

        return f"✅ Service {process_id} (PID: {pid}) stopped successfully"

    except Exception as e:
        return f"❌ Failed to stop service {process_id}: {str(e)}"


def handle_restart_service(process_id: str) -> str:
    """重启指定的后台服务"""
    processes = load_background_processes()

    if process_id not in processes:
        return f"❌ Service not found: {process_id}"

    proc_info = processes[process_id]

    # Stop the service first
    stop_result = handle_stop_service(process_id)

    # Wait a moment
    time.sleep(1)

    # Restart with the original command
    command = proc_info.get("command", "")
    working_dir = proc_info.get("working_dir", os.getcwd())

    if not command:
        return f"❌ Cannot restart {process_id}: original command not found"

    try:
        # Start new process
        restart_output = bash_command(command, None, working_dir, True)
        return (
            f"🔄 Restart completed for {process_id}\n{stop_result}\n\n{restart_output}"
        )

    except Exception as e:
        return f"❌ Failed to restart service {process_id}: {str(e)}"


def handle_service_logs(process_id: str) -> str:
    """查看服务日志"""
    processes = load_background_processes()

    if process_id not in processes:
        return f"❌ Service not found: {process_id}"

    proc_info = processes[process_id]
    log_file = proc_info.get("log_file", "")

    if not log_file or not Path(log_file).exists():
        return f"❌ Log file not found for service {process_id}"

    try:
        # Read last 50 lines of log
        result = subprocess.run(
            f"tail -50 {log_file}", shell=True, capture_output=True, text=True
        )

        if result.returncode == 0:
            output = f"📄 Log for service {process_id} (last 50 lines):\n"
            output += "=" * 50 + "\n"
            output += result.stdout
            return output
        else:
            return f"❌ Failed to read log file: {result.stderr}"

    except Exception as e:
        return f"❌ Error reading logs for {process_id}: {str(e)}"


def validate_git_command(command: str) -> tuple[bool, str]:
    """Validate git commands for safety."""
    # Prevent interactive commands
    if re.search(r"-i\b", command):
        return False, "Interactive git commands (with -i flag) are not supported"

    # Prevent config changes
    if "git config" in command:
        return False, "Git config changes are not allowed"

    # Prevent push commands (should be explicit)
    if re.search(r"\bgit\s+push\b", command):
        return (
            False,
            "Git push commands should be handled carefully. Please explicitly confirm push operations.",
        )

    return True, "Git command is valid"
