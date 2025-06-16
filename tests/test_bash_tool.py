import os
import pytest
import tempfile
import time
from pathlib import Path
import sys

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.tools.bash_tool import (
    bash_command,
    check_command_security,
    BANNED_COMMANDS,
    DISCOURAGED_COMMANDS,
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
