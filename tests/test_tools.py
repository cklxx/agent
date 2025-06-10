#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tools模块测试
"""

import pytest
import logging
from unittest.mock import patch, Mock, call
from src.tools.decorators import log_io, LoggedToolMixin, create_logged_tool


class TestLogIoDecorator:
    """log_io装饰器测试"""

    @patch("src.tools.decorators.logger")
    def test_log_io_basic_function(self, mock_logger):
        """测试log_io装饰器的基本功能"""

        @log_io
        def test_function(x, y):
            return x + y

        result = test_function(1, 2)

        assert result == 3

        # 验证日志调用
        assert mock_logger.info.call_count == 2
        mock_logger.info.assert_has_calls(
            [
                call("Tool test_function called with parameters: 1, 2"),
                call("Tool test_function returned: 3"),
            ]
        )

    @patch("src.tools.decorators.logger")
    def test_log_io_with_kwargs(self, mock_logger):
        """测试log_io装饰器处理关键字参数"""

        @log_io
        def test_function(x, y=10, z=20):
            return x + y + z

        result = test_function(5, y=15, z=25)

        assert result == 45

        # 验证参数日志记录
        call_args = mock_logger.info.call_args_list[0][0][0]
        assert "test_function called with parameters: 5, y=15, z=25" in call_args

        return_args = mock_logger.info.call_args_list[1][0][0]
        assert "test_function returned: 45" in return_args

    @patch("src.tools.decorators.logger")
    def test_log_io_with_mixed_args(self, mock_logger):
        """测试log_io装饰器处理混合参数"""

        @log_io
        def test_function(a, b, c=3, d=4):
            return a * b + c * d

        result = test_function(2, 3, d=5)

        assert result == 2 * 3 + 3 * 5  # 6 + 15 = 21

        # 验证参数记录
        call_args = mock_logger.info.call_args_list[0][0][0]
        assert "2, 3, d=5" in call_args

    @patch("src.tools.decorators.logger")
    def test_log_io_preserves_function_metadata(self, mock_logger):
        """测试log_io装饰器保留函数元数据"""

        @log_io
        def test_function(x):
            """Test function docstring"""
            return x * 2

        assert test_function.__name__ == "test_function"
        assert test_function.__doc__ == "Test function docstring"

    @patch("src.tools.decorators.logger")
    def test_log_io_with_exception(self, mock_logger):
        """测试log_io装饰器处理异常"""

        @log_io
        def test_function(x):
            if x < 0:
                raise ValueError("Negative value")
            return x * 2

        # 正常情况
        result = test_function(5)
        assert result == 10

        # 异常情况
        with pytest.raises(ValueError, match="Negative value"):
            test_function(-1)

        # 验证异常情况下仍然记录了调用日志
        assert any(
            "test_function called with parameters: -1" in str(call)
            for call in mock_logger.info.call_args_list
        )

    @patch("src.tools.decorators.logger")
    def test_log_io_with_complex_return_value(self, mock_logger):
        """测试log_io装饰器处理复杂返回值"""

        @log_io
        def test_function():
            return {"result": [1, 2, 3], "status": "success"}

        result = test_function()
        expected = {"result": [1, 2, 3], "status": "success"}

        assert result == expected

        # 验证复杂返回值被正确记录
        return_call = mock_logger.info.call_args_list[1][0][0]
        assert str(expected) in return_call


class MockBaseTool:
    """Mock基础工具类"""

    def __init__(self, name="MockTool"):
        self.name = name

    def _run(self, input_data):
        return f"Processed: {input_data}"


class TestLoggedToolMixin:
    """LoggedToolMixin测试"""

    @patch("src.tools.decorators.logger")
    def test_logged_tool_mixin_log_operation(self, mock_logger):
        """测试LoggedToolMixin的_log_operation方法"""
        mixin = LoggedToolMixin()

        mixin._log_operation("test_method", "arg1", key="value")

        mock_logger.debug.assert_called_once()
        call_args = mock_logger.debug.call_args[0][0]
        assert (
            "Tool ToolMixin.test_method called with parameters: arg1, key=value"
            in call_args
        )

    @patch("src.tools.decorators.logger")
    def test_logged_tool_mixin_with_mock_tool(self, mock_logger):
        """测试LoggedToolMixin与mock工具的集成"""

        class LoggedMockTool(LoggedToolMixin, MockBaseTool):
            pass

        tool = LoggedMockTool("TestTool")
        result = tool._run("test input")

        assert result == "Processed: test input"

        # 验证日志调用
        assert mock_logger.debug.call_count == 2
        mock_logger.debug.assert_has_calls(
            [
                call("Tool MockTool._run called with parameters: test input"),
                call("Tool MockTool returned: Processed: test input"),
            ]
        )

    @patch("src.tools.decorators.logger")
    def test_logged_tool_mixin_class_name_processing(self, mock_logger):
        """测试LoggedToolMixin的类名处理"""

        class LoggedTestTool(LoggedToolMixin, MockBaseTool):
            pass

        tool = LoggedTestTool()
        tool._log_operation("method", "arg")

        call_args = mock_logger.debug.call_args[0][0]
        # 应该移除"Logged"前缀
        assert "Tool TestTool.method" in call_args


class TestCreateLoggedTool:
    """create_logged_tool工厂函数测试"""

    @patch("src.tools.decorators.logger")
    def test_create_logged_tool_basic(self, mock_logger):
        """测试create_logged_tool基本功能"""
        LoggedMockTool = create_logged_tool(MockBaseTool)

        assert LoggedMockTool.__name__ == "LoggedMockBaseTool"
        assert issubclass(LoggedMockTool, LoggedToolMixin)
        assert issubclass(LoggedMockTool, MockBaseTool)

    @patch("src.tools.decorators.logger")
    def test_create_logged_tool_functionality(self, mock_logger):
        """测试create_logged_tool创建的工具的功能"""
        LoggedMockTool = create_logged_tool(MockBaseTool)

        tool = LoggedMockTool("TestTool")
        result = tool._run("test data")

        assert result == "Processed: test data"

        # 验证日志功能工作
        assert mock_logger.debug.call_count == 2

    def test_create_logged_tool_inheritance_chain(self):
        """测试create_logged_tool的继承链"""
        LoggedMockTool = create_logged_tool(MockBaseTool)

        tool = LoggedMockTool()

        # 验证继承链
        assert isinstance(tool, LoggedToolMixin)
        assert isinstance(tool, MockBaseTool)
        assert hasattr(tool, "_log_operation")
        assert hasattr(tool, "_run")

    def test_create_logged_tool_with_custom_class(self):
        """测试create_logged_tool与自定义类"""

        class CustomTool:
            def __init__(self, value=0):
                self.value = value

            def _run(self, x):
                return self.value + x

        LoggedCustomTool = create_logged_tool(CustomTool)

        assert LoggedCustomTool.__name__ == "LoggedCustomTool"

        tool = LoggedCustomTool(value=10)
        assert tool.value == 10

        result = tool._run(5)
        assert result == 15


class TestIntegration:
    """集成测试"""

    @patch("src.tools.decorators.logger")
    def test_decorator_and_mixin_together(self, mock_logger):
        """测试装饰器和Mixin一起使用"""

        class TestTool(MockBaseTool):
            @log_io
            def process_data(self, data):
                return f"Result: {data}"

        LoggedTestTool = create_logged_tool(TestTool)
        tool = LoggedTestTool()

        # 使用装饰的方法
        result = tool.process_data("test")

        assert result == "Result: test"

        # 验证装饰器的日志
        info_calls = [call for call in mock_logger.info.call_args_list]
        assert len(info_calls) >= 2  # 至少有装饰器的两个日志调用

    @patch("src.tools.decorators.logger")
    def test_logging_levels(self, mock_logger):
        """测试不同的日志级别"""

        @log_io
        def test_func():
            return "test"

        LoggedMockTool = create_logged_tool(MockBaseTool)
        tool = LoggedMockTool()

        # 装饰器使用info级别
        test_func()
        assert mock_logger.info.called

        # Mixin使用debug级别
        tool._run("test")
        assert mock_logger.debug.called
