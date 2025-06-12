# SPDX-License-Identifier: MIT

"""
Bash command execution tool with security restrictions and git integration.
"""

import os
import subprocess
import logging
import re
import json
import time
from typing import Optional, List, Set, Dict
from pathlib import Path
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# Banned commands for security
BANNED_COMMANDS = {
    "alias",
    "curl",
    "curlie",
    "wget",
    "axel",
    "aria2c",
    "nc",
    "telnet",
    "lynx",
    "w3m",
    "links",
    "httpie",
    "xh",
    "http-prompt",
    "chrome",
    "firefox",
    "safari",
}

# Commands that should use specialized tools instead
DISCOURAGED_COMMANDS = {
    "find": "Use GrepTool or SearchGlobTool instead",
    "grep": "Use GrepTool instead",
    "cat": "Use View tool instead",
    "head": "Use View tool instead",
    "tail": "Use View tool instead",
    "ls": "Use List tool instead",
}

MAX_OUTPUT_LENGTH = 30000

# 后台进程管理
BACKGROUND_PROCESSES_FILE = Path("/tmp/agent_background_processes.json")


def load_background_processes() -> Dict[str, Dict]:
    """加载后台进程记录"""
    if not BACKGROUND_PROCESSES_FILE.exists():
        return {}
    try:
        with open(BACKGROUND_PROCESSES_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def save_background_processes(processes: Dict[str, Dict]):
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
    """Check if command is allowed based on security policy."""
    # Extract the first command from the command line
    first_command = command.strip().split()[0] if command.strip() else ""
    base_command = os.path.basename(first_command)

    # Check banned commands
    if base_command in BANNED_COMMANDS:
        return (
            False,
            f"Command '{base_command}' is banned for security reasons. Banned commands: {', '.join(sorted(BANNED_COMMANDS))}",
        )

    # Check discouraged commands
    if base_command in DISCOURAGED_COMMANDS:
        suggestion = DISCOURAGED_COMMANDS[base_command]
        return False, f"Command '{base_command}' should not be used. {suggestion}"

    return True, "Command is allowed"


def execute_bash_command(
    command: str,
    timeout_ms: Optional[int] = None,
    cwd: Optional[str] = None,
    run_in_background: bool = False,
) -> str:
    """Execute a bash command with proper error handling and output truncation."""
    try:
        # Set timeout (default 30 minutes, max 10 minutes for tool)
        timeout_seconds = min((timeout_ms or 1800000) / 1000, 600)  # Max 10 minutes

        # Use provided cwd or current directory
        working_dir = cwd or os.getcwd()

        # Check if this is a long-running service command
        service_indicators = [
            "python -m",
            "uvicorn",
            "flask run",
            "django runserver",
            "node",
            "npm start",
            "yarn start",
            "serve",
            "http-server",
        ]
        is_service_command = any(
            indicator in command.lower() for indicator in service_indicators
        )

        # If run_in_background is True or this looks like a service command, run in background
        if run_in_background or is_service_command:
            # Create unique log file for this service
            timestamp = int(time.time())
            log_file = f"/tmp/service_{timestamp}.log"

            # Prepare background command
            bg_command = f"nohup {command} > {log_file} 2>&1 & echo $!"

            # Start the background process and get PID
            result = subprocess.run(
                bg_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=5,  # Short timeout for background startup
                cwd=working_dir,
            )

            if result.returncode == 0:
                pid = result.stdout.strip()
                if pid:
                    # Record the background process
                    process_id = add_background_process(
                        pid, command, working_dir, log_file
                    )

                    output = f"✅ Service started in background\n"
                    output += f"📋 Process ID: {process_id}\n"
                    output += f"🔢 System PID: {pid}\n"
                    output += f"📁 Working Directory: {working_dir}\n"
                    output += f"📄 Log File: {log_file}\n"
                    output += f"🛑 To stop this service: bash_command('stop_service {process_id}')\n"
                    output += f"📊 To check status: bash_command('list_services')\n"

                    return output
                else:
                    return f"❌ Failed to get process ID for background service"
            else:
                return f"❌ Failed to start background service:\n{result.stderr}"

        # Execute command normally for non-service commands
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            cwd=working_dir,
        )

        # Combine stdout and stderr
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            if output:
                output += "\n" + result.stderr
            else:
                output = result.stderr

        # Add exit code information
        if result.returncode != 0:
            output += f"\nExit code: {result.returncode}"

        # Truncate output if too long
        if len(output) > MAX_OUTPUT_LENGTH:
            truncated_length = (
                MAX_OUTPUT_LENGTH - 200
            )  # Leave space for truncation message
            output = (
                output[:truncated_length]
                + f"\n\n... (output truncated, showing first {truncated_length} characters of {len(output)} total)"
            )

        return output or "(no output)"

    except subprocess.TimeoutExpired:
        return f"Command timed out after {timeout_seconds} seconds"
    except Exception as e:
        return f"Error executing command: {str(e)}"


@tool
def bash_command(
    command: str,
    timeout: Optional[int] = None,
    working_directory: Optional[str] = None,
    run_in_background: bool = False,
) -> str:
    """
    Executes a given bash command in a persistent shell session with optional timeout, ensuring proper
    handling and security measures.

    Before executing the command, please follow these steps:
    1. Directory Verification:
       - If the command will create new directories or files, first use the LS tool to verify the parent directory exists and is the correct location
       - For example, before running "mkdir foo/bar", first use LS to check that "foo" exists and is the intended parent directory
    2. Security Check:
       - For security and to limit the threat of a prompt injection attack, some commands are limited or banned. If you use a disallowed command, you will receive an error message explaining the restriction. Explain the error to the User.
       - Verify that the command is not one of the banned commands: alias, curl, curlie, wget, axel, aria2c, nc, telnet, lynx, w3m, links, httpie, xh, http-prompt, chrome, firefox, safari.
    3. Command Execution:
       - After ensuring proper quoting, execute the command.
       - Capture the output of the command.
    4. Output Processing:
       - If the output exceeds 30000 characters, output will be truncated before being returned to you.
       - Prepare the output for display to the user.
    5. Return Result:
       - Provide the processed output of the command.
       - If any errors occurred during execution, include those in the output.

    Usage notes:
      - The command argument is required.
      - You can specify an optional timeout in milliseconds (up to 600000ms / 10 minutes). If not specified, commands will timeout after 30 minutes.
      - You can specify an optional working_directory to execute the command in a specific directory.
      - You can specify run_in_background=True to run long-running services in background. The tool also auto-detects common service commands.
      - VERY IMPORTANT: You MUST avoid using search commands like `find` and `grep`. Instead use GrepTool, SearchGlobTool, or dispatch_agent to search. You MUST avoid read tools like `cat`, `head`, `tail`, and `ls`, and use View and List to read files.
      - When issuing multiple commands, use the ';' or '&&' operator to separate them. DO NOT use newlines (newlines are ok in quoted strings).
      - IMPORTANT: All commands share the same shell session. Shell state (environment variables, virtual environments, current directory, etc.) persist between commands. For example, if you set an environment variable as part of a command, the environment variable will persist for subsequent commands.
      - Try to maintain your current working directory throughout the session by using absolute paths and avoiding usage of `cd`. You may use `cd` if the User explicitly requests it.

    Background Service Management:
      - list_services: Show all running background services
      - stop_service <process_id>: Stop a specific background service
      - restart_service <process_id>: Restart a background service
      - service_logs <process_id>: View logs of a background service

    Args:
        command: The command to execute
        timeout: Optional timeout in milliseconds (max 600000)
        working_directory: Optional working directory to execute the command in
        run_in_background: Whether to run the command in background (useful for long-running services)

    Returns:
        The command output and any error messages
    """
    try:
        # Security check
        is_allowed, security_message = check_command_security(command)
        if not is_allowed:
            return f"Security Error: {security_message}"

        # Handle service management commands
        if command.startswith("list_services"):
            return handle_list_services()
        elif command.startswith("stop_service "):
            process_id = command.replace("stop_service ", "").strip()
            return handle_stop_service(process_id)
        elif command.startswith("restart_service "):
            process_id = command.replace("restart_service ", "").strip()
            return handle_restart_service(process_id)
        elif command.startswith("service_logs "):
            process_id = command.replace("service_logs ", "").strip()
            return handle_service_logs(process_id)

        # Log command execution
        working_dir_info = f" in {working_directory}" if working_directory else ""
        logger.info(f"Executing bash command: {command[:100]}...{working_dir_info}")

        # Execute command with the specified working directory
        output = execute_bash_command(
            command, timeout, working_directory, run_in_background
        )

        # Handle git-specific commands with special formatting
        if command.strip().startswith(("git ", "gh ")):
            # For git commands, format output nicely
            if "git status" in command:
                output = f"Git Status:\n{output}"
            elif "git log" in command:
                output = f"Git Log:\n{output}"
            elif "git diff" in command:
                output = f"Git Diff:\n{output}"
            elif "gh pr create" in command:
                output = f"Pull Request Created:\n{output}"

        return output

    except Exception as e:
        error_msg = f"Bash tool error: {str(e)}"
        logger.error(error_msg)
        return error_msg


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

    for proc_id, proc_info in processes.items():
        pid = proc_info.get("pid", "")
        status = "🟢 Running" if is_process_running(pid) else "🔴 Stopped"

        # Update status in records
        if not is_process_running(pid):
            proc_info["status"] = "stopped"

        output += f"🔷 ID: {proc_id}\n"
        output += f"   Status: {status}\n"
        output += f"   PID: {pid}\n"
        output += f"   Command: {proc_info.get('command', 'N/A')}\n"
        output += f"   Directory: {proc_info.get('working_dir', 'N/A')}\n"
        output += f"   Log: {proc_info.get('log_file', 'N/A')}\n"
        output += f"   Started: {time.ctime(proc_info.get('start_time', 0))}\n"
        output += "-" * 30 + "\n"

    # Save updated status
    save_background_processes(processes)

    output += "\n🛠️ Management Commands:\n"
    output += "• stop_service <process_id> - Stop a service\n"
    output += "• restart_service <process_id> - Restart a service\n"
    output += "• service_logs <process_id> - View service logs\n"

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
        restart_output = execute_bash_command(command, None, working_dir, True)
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
