#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Workspace Tools 模块详细测试
"""

import os
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, Mock
import sys

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.tools.workspace_tools import (
    resolve_workspace_path,
    create_workspace_aware_tools,
    get_workspace_tools,
    create_workspace_tool_factory,
)


class TestResolveWorkspacePath:
    """测试workspace路径解析功能"""

    def test_resolve_relative_path_with_workspace(self):
        """测试相对路径解析"""
        workspace = "/home/user/project"
        file_path = "src/main.py"
        result = resolve_workspace_path(file_path, workspace)
        expected = "/home/user/project/src/main.py"
        assert result == expected

    def test_resolve_absolute_path_unchanged(self):
        """测试绝对路径保持不变"""
        workspace = "/home/user/project"
        file_path = "/absolute/path/file.py"
        result = resolve_workspace_path(file_path, workspace)
        assert result == file_path

    def test_resolve_without_workspace(self):
        """测试无workspace时的行为"""
        file_path = "src/main.py"
        result = resolve_workspace_path(file_path, None)
        assert result == file_path

    def test_resolve_empty_workspace(self):
        """测试空workspace"""
        file_path = "src/main.py"
        result = resolve_workspace_path(file_path, "")
        assert result == file_path

    def test_resolve_current_directory(self):
        """测试当前目录"""
        workspace = "/home/user/project"
        file_path = "."
        result = resolve_workspace_path(file_path, workspace)
        expected = "/home/user/project"
        assert result == expected


class TestWorkspaceToolsCreation:
    """测试workspace工具创建"""

    def setup_method(self):
        """设置测试环境"""
        self.temp_workspace = tempfile.mkdtemp()

    def teardown_method(self):
        """清理测试环境"""
        if os.path.exists(self.temp_workspace):
            shutil.rmtree(self.temp_workspace)

    def test_create_workspace_aware_tools_basic(self):
        """测试基本workspace工具创建"""
        tools = create_workspace_aware_tools("/test/workspace")

        # 验证返回的是工具列表
        assert isinstance(tools, list)
        assert len(tools) > 0

        # 验证所有工具都有name属性
        tool_names = [tool.name for tool in tools]
        expected_tools = [
            "view_file",
            "list_files",
            "glob_search",
            "grep_search",
            "edit_file",
            "replace_file",
            "notebook_read",
            "notebook_edit_cell",
            "bash_command",
        ]

        for expected_tool in expected_tools:
            assert expected_tool in tool_names

    def test_get_workspace_tools_dict(self):
        """测试获取workspace工具字典"""
        tools = get_workspace_tools("/test/workspace")

        # 验证返回的是列表而不是字典
        assert isinstance(tools, list)

    def test_workspace_tool_factory_from_state(self):
        """测试从state创建工具工厂"""
        state = {"workspace": "/test/workspace"}
        factory = create_workspace_tool_factory(state)

        # 验证工厂函数可调用
        assert callable(factory)

        # 验证工厂返回工具
        tools = factory()
        assert isinstance(tools, list)
        assert len(tools) > 0


class TestWorkspaceAwareToolsIntegration:
    """测试workspace感知工具的集成功能"""

    def setup_method(self):
        """设置测试环境"""
        self.temp_workspace = tempfile.mkdtemp()
        self.test_file = os.path.join(self.temp_workspace, "test.txt")
        with open(self.test_file, "w") as f:
            f.write("Hello, World!")

    def teardown_method(self):
        """清理测试环境"""
        if os.path.exists(self.temp_workspace):
            shutil.rmtree(self.temp_workspace)

    def test_view_file_with_workspace_resolution(self):
        """测试view_file的workspace路径解析"""
        tools = get_workspace_tools(self.temp_workspace)
        # 返回的是列表，需要找到view_file工具
        view_file_tool = next(tool for tool in tools if tool.name == "view_file")

        # 使用相对路径访问文件
        result = view_file_tool.func("test.txt")
        assert "Hello, World!" in result

    def test_list_files_with_workspace_resolution(self):
        """测试list_files的workspace路径解析"""
        tools = get_workspace_tools(self.temp_workspace)
        # 返回的是列表，需要找到list_files工具
        list_files_tool = next(tool for tool in tools if tool.name == "list_files")

        # 列出workspace根目录
        result = list_files_tool.func(".")
        assert "test.txt" in result

    @patch("subprocess.Popen")
    def test_bash_command_with_workspace_directory(self, mock_popen):
        """测试bash_command的workspace工作目录设置"""
        # Mock the Popen process
        mock_process = Mock()
        mock_process.stdout.readline.side_effect = ["test output\n", ""]
        mock_process.poll.return_value = 0
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process

        tools = get_workspace_tools(self.temp_workspace)
        # 返回的是列表，需要找到bash_command工具
        bash_tool = next(tool for tool in tools if tool.name == "bash_command")

        # 执行命令
        result = bash_tool.func("pwd")

        # 验证Popen被调用
        mock_popen.assert_called()
        call_args = mock_popen.call_args
        # 检查工作目录是否正确设置在命令中
        command_arg = call_args[0][0]  # 第一个位置参数是命令
        assert self.temp_workspace in command_arg


class TestWorkspaceToolsErrorHandling:
    """测试workspace工具的错误处理"""

    def test_tools_with_nonexistent_workspace(self):
        """测试不存在的workspace"""
        nonexistent_workspace = "/nonexistent/workspace"
        tools = get_workspace_tools(nonexistent_workspace)

        # 工具应该能创建，但使用时会报错
        assert isinstance(tools, list)
        assert len(tools) > 0

    def test_tools_with_none_workspace(self):
        """测试None workspace"""
        tools = get_workspace_tools(None)

        # 应该能正常创建工具
        assert isinstance(tools, list)
        assert len(tools) > 0

    def test_factory_with_empty_state(self):
        """测试空state"""
        factory = create_workspace_tool_factory({})
        tools = factory()

        # 应该能正常创建工具
        assert isinstance(tools, list)
        assert len(tools) > 0


class TestWorkspaceToolsDocumentation:
    """测试workspace工具的文档字符串"""

    def test_all_tools_have_docstrings(self):
        """测试所有工具都有文档字符串"""
        tools = get_workspace_tools("/test")

        for tool in tools:
            assert hasattr(tool, "description")
            assert tool.description is not None
            assert len(tool.description.strip()) > 0

    def test_tool_descriptions_are_concise(self):
        """测试工具描述简洁性"""
        tools = get_workspace_tools("/test")

        for tool in tools:
            description = tool.description.strip()
            # 文档应该简洁（不超过500字符）
            assert len(description) < 500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
