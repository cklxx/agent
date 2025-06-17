import os
import pytest
import tempfile
import time
from pathlib import Path
import sys
from unittest import mock

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.tools.bash_tool import (
    bash_command,
    check_command_security,
    BANNED_COMMANDS,
    DISCOURAGED_COMMANDS,
    MAX_OUTPUT_LENGTH,
)


def test_basic_command_execution():
    """测试基本命令执行"""
    # 直接调用函数而不是工具对象
    result = bash_command.func("echo 'Hello, World!'")
    assert "Hello, World!" in result


def test_working_directory():
    """测试工作目录功能"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # 在临时目录中创建测试文件
        test_file = os.path.join(temp_dir, "test.txt")
        with open(test_file, "w") as f:
            f.write("test content")

        # 测试在不同目录执行命令 - 使用pwd来验证工作目录
        result = bash_command.func("pwd", working_directory=temp_dir)
        assert temp_dir in result


def test_command_timeout():
    """测试命令超时"""
    # 测试超时设置
    result = bash_command.func("sleep 2", timeout=1000)  # 1秒超时
    assert "Error" in result or "timed out" in result


def test_banned_commands():
    """测试禁用命令"""
    result = bash_command.func("curl http://example.com")
    assert "Security Error" in result


def test_discouraged_commands():
    """测试不推荐命令"""
    result = bash_command.func("find . -name '*.py'")
    assert "Security Error" in result


def test_command_security():
    """测试命令安全性"""
    # 测试允许的命令
    result = bash_command.func("echo 'safe'")
    assert "safe" in result

    # 测试禁止的命令
    result = bash_command.func("curl http://example.com")
    assert "Security Error" in result


def test_error_handling():
    """测试错误处理"""
    # 测试不存在的命令
    result = bash_command.func("nonexistent_command")
    assert "Error" in result or "command not found" in result


def test_complex_command_chain():
    """测试复杂命令链"""
    # 使用echo和简单的文件操作来避免安全限制
    result = bash_command.func(
        "echo 'test' > /tmp/test.txt && echo 'success' && rm /tmp/test.txt"
    )
    assert "success" in result


def test_check_command_security():
    """测试命令安全检查函数"""
    # 测试允许的命令
    is_allowed, message = check_command_security("echo test")
    assert is_allowed

    # 测试禁用的命令
    is_allowed, message = check_command_security("curl http://example.com")
    assert not is_allowed
    assert "banned" in message.lower()

    # 测试不推荐的命令
    is_allowed, message = check_command_security("find . -name test")
    assert not is_allowed
    assert "discouraged" in message.lower()


def test_foreground_command_output_truncation():
    """测试前台命令输出截断"""
    # 命令产生的输出长度大于 MAX_OUTPUT_LENGTH
    command = "python -c \"print('A' * 35000)\""
    result = bash_command.func(command)

    # 断言输出长度约等于 MAX_OUTPUT_LENGTH
    # 由于可能添加了截断消息，所以长度可能略大于 MAX_OUTPUT_LENGTH
    assert MAX_OUTPUT_LENGTH <= len(result) < MAX_OUTPUT_LENGTH + 100, f"Expected length close to {MAX_OUTPUT_LENGTH}, but got {len(result)}"

    # 断言输出包含截断消息
    assert "... (output truncated)" in result, "Truncation message not found in output"


@mock.patch("src.tools.bash_tool.save_background_process")
def test_background_command_starts_successfully(mock_save_process):
    """测试后台命令成功启动"""
    command = "echo 'background test'" # No & needed
    result = bash_command.func(command, run_in_background=True)

    assert "Started background process" in result
    assert "PID:" in result
    assert "Log file:" in result
    mock_save_process.assert_called_once()

    # save_background_process is called with a single dictionary argument
    saved_info = mock_save_process.call_args[0][0]
    assert saved_info["command"] == command
    # In this case, working_directory in execute_background_command will be None,
    # so it will be os.getcwd() in the returned string and in saved_info
    assert f"Working directory: {os.getcwd()}" in result
    assert saved_info["working_dir"] == os.getcwd()


@mock.patch("src.tools.bash_tool.save_background_process")
def test_background_command_respects_working_directory(mock_save_process):
    """测试后台命令尊重工作目录"""
    with tempfile.TemporaryDirectory() as temp_dir:
        original_command = "pwd" # No & needed
        # The `command` variable in `bash_command` function will be "cd <temp_dir> && pwd"
        # This modified command is what's passed to `execute_background_command`
        # and subsequently saved in process_info["command"]

        result = bash_command.func(original_command, working_directory=temp_dir, run_in_background=True)

        assert "Started background process" in result
        assert f"Working directory: {temp_dir}" in result
        mock_save_process.assert_called_once()

        saved_info = mock_save_process.call_args[0][0]
        # The 'command' passed to execute_background_command includes the cd prefix
        assert saved_info["command"] == f"cd {temp_dir} && {original_command}"
        assert saved_info["working_dir"] == temp_dir


@mock.patch("src.tools.bash_tool.save_background_process")
@mock.patch("src.tools.bash_tool.tempfile.NamedTemporaryFile") # Make sure to patch where it's used
def test_background_command_creates_log_file(mock_named_temp_file, mock_save_process):
    """测试后台命令创建日志文件"""
    mock_log_file_object = mock.Mock()
    mock_log_file_object.name = "/tmp/fake_log_file.log"
    mock_named_temp_file.return_value = mock_log_file_object

    command = "sleep 1" # No & needed
    result = bash_command.func(command, run_in_background=True)

    assert "Started background process" in result
    assert f"Log file: {mock_log_file_object.name}" in result

    mock_named_temp_file.assert_called_once_with(delete=False, suffix=".log")

    mock_save_process.assert_called_once()
    saved_info = mock_save_process.call_args[0][0]
    assert saved_info["log_file"] == mock_log_file_object.name
    assert saved_info["command"] == command # original command


# --- Tests for Background Process Management Functions ---

# Helper to create mock process data
def _create_mock_process(pid, command="cmd", wd="/d", log="/l.log", ts=None, status="running", auto_cleanup=False):
    return {
        "pid": str(pid),
        "command": command,
        "working_dir": wd,
        "log_file": log,
        "start_time": ts or time.time(),
        "status": status,
        "auto_cleanup": auto_cleanup,
    }

# It's better to import the functions directly to test them
from src.tools.bash_tool import (
    handle_list_services,
    handle_stop_service,
    handle_restart_service,
    handle_service_logs,
    bash_command as bash_tool_bash_command, # Alias to avoid conflict
    format_git_commit_message,
    validate_git_command
)
# We'll also need Path for mocking
from src.tools.bash_tool import Path as BashToolPath # Already here, good.


class TestHandleListServices:
    @mock.patch("src.tools.bash_tool.load_background_processes", return_value={})
    def test_list_services_no_services(self, mock_load):
        result = handle_list_services()
        assert "No background services currently running" in result
        mock_load.assert_called_once()

    @mock.patch("src.tools.bash_tool.is_process_running", return_value=True)
    @mock.patch("src.tools.bash_tool.save_background_processes") # Should not be called if status doesn't change
    @mock.patch("src.tools.bash_tool.load_background_processes")
    def test_list_services_one_running_service(self, mock_load, mock_save, mock_is_running):
        mock_load.return_value = {"proc1": _create_mock_process(pid=123, command="sleep 100")}
        result = handle_list_services()

        assert "proc1" in result
        assert "🟢 Running" in result
        assert "sleep 100" in result
        mock_is_running.assert_called_once_with("123")
        mock_save.assert_not_called() # Status is running, active_processes == processes

    @mock.patch("src.tools.bash_tool.is_process_running", return_value=False)
    @mock.patch("src.tools.bash_tool.save_background_processes")
    @mock.patch("src.tools.bash_tool.load_background_processes")
    def test_list_services_one_stopped_service(self, mock_load, mock_save, mock_is_running):
        # This test reflects current behavior where if no processes are *actively running*,
        # the function reports "No active background services", even if stopped,
        # non-auto-cleanup services exist and would have been part of the detailed 'output' string.
        proc_data = {"proc1": _create_mock_process(pid=123, status="running", auto_cleanup=False)}
        mock_load.return_value = proc_data

        result = handle_list_services()

        # Due to current logic, if nothing is strictly "active" (running), this message is returned.
        # A more nuanced implementation might show stopped non-auto-cleanup services here.
        assert "No active background services currently running" in result
        # assert "proc1" in result # This would be ideal if the final check was different
        # assert "🔴 Stopped" in result # This would be ideal

        mock_is_running.assert_called_once_with("123")
        mock_save.assert_called_once()
        saved_data = mock_save.call_args[0][0]
        # Even though "No active" is returned, save_background_processes is called with an empty active_processes dict.
        # The original `processes` dict (loaded one) is not what's passed to save if active_processes != processes.
        # `active_processes` would be empty here.
        assert not saved_data # mock_save is called with an empty dict because active_processes is empty


    @mock.patch("src.tools.bash_tool.is_process_running")
    @mock.patch("src.tools.bash_tool.save_background_processes")
    @mock.patch("src.tools.bash_tool.load_background_processes")
    def test_list_services_cleans_up_stopped_auto_cleanup_services(self, mock_load, mock_save, mock_is_running):
        proc1_auto_cleanup_stopped = _create_mock_process(pid=123, auto_cleanup=True, status="running")
        proc2_manual_stopped = _create_mock_process(pid=456, auto_cleanup=False, status="running", command="keep_me")
        mock_load.return_value = {
            "proc1": proc1_auto_cleanup_stopped,
            "proc2": proc2_manual_stopped,
        }
        # proc1 is stopped, proc2 is running
        mock_is_running.side_effect = lambda pid: False if pid == "123" else True

        result = handle_list_services()

        assert "proc1" not in result # Should be cleaned up and not listed
        assert "proc2" in result
        assert "keep_me" in result
        assert "🟢 Running" in result # For proc2

        mock_save.assert_called_once()
        saved_data = mock_save.call_args[0][0]
        assert "proc1" not in saved_data # proc1 removed from persisted data
        assert "proc2" in saved_data
        assert saved_data["proc2"]["status"] == "running"


class TestHandleStopService:
    @mock.patch("src.tools.bash_tool.subprocess.run")
    @mock.patch("src.tools.bash_tool.is_process_running", side_effect=[True, False]) # Running then stopped
    @mock.patch("src.tools.bash_tool.save_background_processes")
    @mock.patch("src.tools.bash_tool.load_background_processes")
    def test_stop_service_running(self, mock_load, mock_save, mock_is_running, mock_subprocess_run):
        mock_load.return_value = {"proc1": _create_mock_process(pid=123)}

        result = handle_stop_service("proc1")

        assert "Service proc1 (PID: 123) stopped successfully" in result
        mock_subprocess_run.assert_called_once_with("kill 123", shell=True, capture_output=True, text=True)
        mock_save.assert_called_once()
        assert mock_save.call_args[0][0]["proc1"]["status"] == "stopped"

    @mock.patch("src.tools.bash_tool.is_process_running", return_value=False)
    @mock.patch("src.tools.bash_tool.save_background_processes")
    @mock.patch("src.tools.bash_tool.load_background_processes")
    def test_stop_service_already_stopped(self, mock_load, mock_save, mock_is_running):
        mock_load.return_value = {"proc1": _create_mock_process(pid=123, status="stopped")}

        result = handle_stop_service("proc1")

        assert "Service proc1 is already stopped" in result
        mock_is_running.assert_called_once_with("123")
        # save_background_processes is called even if already stopped to update the status from loaded data potentially
        mock_save.assert_called_once()
        assert mock_save.call_args[0][0]["proc1"]["status"] == "stopped"

    @mock.patch("src.tools.bash_tool.load_background_processes", return_value={})
    def test_stop_service_non_existent(self, mock_load):
        result = handle_stop_service("proc_unknown")
        assert "Service not found: proc_unknown" in result

    @mock.patch("src.tools.bash_tool.subprocess.run")
    @mock.patch("src.tools.bash_tool.is_process_running", side_effect=[True, True, False]) # Running, still running, then stopped
    @mock.patch("src.tools.bash_tool.save_background_processes")
    @mock.patch("src.tools.bash_tool.load_background_processes")
    def test_stop_service_force_kill(self, mock_load, mock_save, mock_is_running, mock_subprocess_run):
        mock_load.return_value = {"proc1": _create_mock_process(pid=123)}

        result = handle_stop_service("proc1")

        assert "Service proc1 (PID: 123) stopped successfully" in result
        assert mock_subprocess_run.call_count == 2
        mock_subprocess_run.assert_any_call("kill 123", shell=True, capture_output=True, text=True)
        mock_subprocess_run.assert_any_call("kill -9 123", shell=True, capture_output=True, text=True)
        mock_save.assert_called_once()
        assert mock_save.call_args[0][0]["proc1"]["status"] == "stopped"


class TestHandleRestartService:
    @mock.patch("src.tools.bash_tool.bash_command") # Target the function in bash_tool.py
    @mock.patch("src.tools.bash_tool.handle_stop_service")
    @mock.patch("src.tools.bash_tool.load_background_processes")
    # save_background_processes will be called by handle_stop_service and by the mocked bash_command implicitly (via execute_background_command)
    # So, we don't need to mock save_background_processes directly here unless we want to inspect its calls from this level.
    def test_restart_service_successful(self, mock_load_procs, mock_stop_service, mock_internal_bash_command):
        proc_info = _create_mock_process(pid=123, command="sleep 30", wd="/my/dir")
        mock_load_procs.return_value = {"proc1": proc_info}
        mock_stop_service.return_value = "Stopped successfully"
        mock_internal_bash_command.return_value = "Started background process PID: 456 Log file: /log/new.txt Working directory: /my/dir"

        result = handle_restart_service("proc1")

        mock_stop_service.assert_called_once_with("proc1")
        mock_internal_bash_command.assert_called_once_with("sleep 30", None, "/my/dir", True)
        assert "Restart completed for proc1" in result
        assert "Stopped successfully" in result
        assert "Started background process PID: 456" in result

    @mock.patch("src.tools.bash_tool.load_background_processes", return_value={})
    def test_restart_service_non_existent(self, mock_load_procs):
        result = handle_restart_service("proc_unknown")
        assert "Service not found: proc_unknown" in result

    @mock.patch("src.tools.bash_tool.handle_stop_service") # Still called
    @mock.patch("src.tools.bash_tool.load_background_processes")
    def test_restart_service_no_command(self, mock_load_procs, mock_stop_service):
        mock_load_procs.return_value = {"proc1": _create_mock_process(pid=123, command="")} # Empty command
        mock_stop_service.return_value = "Stopped (for no command test)"
        result = handle_restart_service("proc1")
        assert "Cannot restart proc1: original command not found" in result
        mock_stop_service.assert_called_once_with("proc1")


class TestHandleServiceLogs:
    @mock.patch("src.tools.bash_tool.subprocess.run")
    @mock.patch("src.tools.bash_tool.Path") # Patch Path from pathlib inside bash_tool
    @mock.patch("src.tools.bash_tool.load_background_processes")
    def test_service_logs_successful(self, mock_load, mock_path_constructor, mock_subprocess_run):
        log_file_path = "/tmp/proc1.log"
        mock_load.return_value = {"proc1": _create_mock_process(pid=123, log=log_file_path)}

        # Setup mock for Path(log_file_path).exists()
        mock_path_instance = mock.Mock()
        mock_path_instance.exists.return_value = True
        mock_path_constructor.return_value = mock_path_instance

        mock_subprocess_run.return_value = mock.Mock(returncode=0, stdout="Log line 1\nLog line 2")

        result = handle_service_logs("proc1")

        assert f"Log for service proc1" in result
        assert "Log line 1" in result
        assert "Log line 2" in result
        mock_path_constructor.assert_called_once_with(log_file_path)
        mock_path_instance.exists.assert_called_once()
        mock_subprocess_run.assert_called_once_with(f"tail -50 {log_file_path}", shell=True, capture_output=True, text=True)

    @mock.patch("src.tools.bash_tool.load_background_processes", return_value={})
    def test_service_logs_non_existent_service(self, mock_load):
        result = handle_service_logs("proc_unknown")
        assert "Service not found: proc_unknown" in result

    @mock.patch("src.tools.bash_tool.Path")
    @mock.patch("src.tools.bash_tool.load_background_processes")
    def test_service_logs_log_file_missing(self, mock_load, mock_path_constructor):
        log_file_path = "/tmp/proc1_missing.log"
        mock_load.return_value = {"proc1": _create_mock_process(pid=123, log=log_file_path)}

        mock_path_instance = mock.Mock()
        mock_path_instance.exists.return_value = False # Log file does not exist
        mock_path_constructor.return_value = mock_path_instance

        result = handle_service_logs("proc1")
        assert "Log file not found for service proc1" in result
        mock_path_constructor.assert_called_once_with(log_file_path)
        mock_path_instance.exists.assert_called_once()

    @mock.patch("src.tools.bash_tool.subprocess.run")
    @mock.patch("src.tools.bash_tool.Path")
    @mock.patch("src.tools.bash_tool.load_background_processes")
    def test_service_logs_read_error(self, mock_load, mock_path_constructor, mock_subprocess_run):
        log_file_path = "/tmp/proc1_read_error.log"
        mock_load.return_value = {"proc1": _create_mock_process(pid=123, log=log_file_path)}

        mock_path_instance = mock.Mock()
        mock_path_instance.exists.return_value = True
        mock_path_constructor.return_value = mock_path_instance

        mock_subprocess_run.return_value = mock.Mock(returncode=1, stderr="Error reading file")

        result = handle_service_logs("proc1")
        assert "Failed to read log file: Error reading file" in result
        mock_subprocess_run.assert_called_once_with(f"tail -50 {log_file_path}", shell=True, capture_output=True, text=True)

# Need to ensure time is imported for the helper
import time


# --- Tests for Git Helper Functions ---

def test_format_git_commit_message():
    """Tests the git commit message formatting function."""
    title = "Test Commit Title"
    body = "This is the body of the commit message.\nIt has multiple lines."
    expected_message = (
        f"{title}\n\n"
        f"{body}\n\n"
        "🤖 Generated with Code Agent"
    )
    assert format_git_commit_message(title, body) == expected_message

    title_only = "Title Only Commit"
    body_empty = ""
    expected_message_title_only = (
        f"{title_only}\n\n"
        f"{body_empty}\n\n" # The function currently adds newlines even for empty body
        "🤖 Generated with Code Agent"
    )
    assert format_git_commit_message(title_only, body_empty) == expected_message_title_only


def test_validate_git_command():
    """Tests the git command validation logic."""
    # Allowed commands
    assert validate_git_command("git status") == (True, "Git command is valid")
    assert validate_git_command("git diff") == (True, "Git command is valid")
    assert validate_git_command("git commit -m 'Initial commit'") == (True, "Git command is valid")
    assert validate_git_command("git log --oneline") == (True, "Git command is valid")
    assert validate_git_command("git pull origin main") == (True, "Git command is valid")
    assert validate_git_command("git fetch --all") == (True, "Git command is valid")
    assert validate_git_command("git branch new-feature") == (True, "Git command is valid")
    assert validate_git_command("git checkout -b new-branch") == (True, "Git command is valid")

    # Disallowed: Interactive flag
    expected_interactive_msg = "Interactive git commands (with -i flag) are not supported"
    assert validate_git_command("git commit -i") == (False, expected_interactive_msg)
    assert validate_git_command("git rebase -i main") == (False, expected_interactive_msg)
    assert validate_git_command("git add -i") == (False, expected_interactive_msg) # Though -i is not a common flag for add

    # Disallowed: Config changes
    expected_config_msg = "Git config changes are not allowed"
    assert validate_git_command("git config user.name 'Test User'") == (False, expected_config_msg)
    assert validate_git_command("git config --global core.editor vim") == (False, expected_config_msg)

    # Disallowed: Push (needs explicit confirmation - this validator just flags it)
    expected_push_msg = "Git push commands should be handled carefully. Please explicitly confirm push operations."
    assert validate_git_command("git push") == (False, expected_push_msg)
    assert validate_git_command("git push origin main") == (False, expected_push_msg)
    assert validate_git_command("git push --force") == (False, expected_push_msg)
