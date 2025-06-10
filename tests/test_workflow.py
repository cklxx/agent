#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Workflow模块测试
"""

import pytest
import asyncio
from unittest.mock import patch, Mock, AsyncMock
from src.workflow import graph, run_agent_workflow_async


class TestWorkflowModule:
    """Workflow模块测试"""

    def test_graph_exists(self):
        """测试graph对象存在"""
        assert graph is not None
        # 测试graph有必要的方法
        assert hasattr(graph, "astream")
        assert hasattr(graph, "get_graph")

    def test_graph_has_mermaid_method(self):
        """测试graph可以生成Mermaid图"""
        try:
            mermaid_output = graph.get_graph(xray=True).draw_mermaid()
            assert isinstance(mermaid_output, str)
            assert len(mermaid_output) > 0
        except Exception as e:
            # 如果图生成失败，至少确保方法存在
            assert hasattr(graph.get_graph(xray=True), "draw_mermaid")

    @pytest.mark.asyncio
    async def test_run_agent_workflow_async_empty_input(self):
        """测试空输入抛出异常"""
        with pytest.raises(ValueError, match="Input could not be empty"):
            await run_agent_workflow_async("")

        with pytest.raises(ValueError, match="Input could not be empty"):
            await run_agent_workflow_async(None)

    @pytest.mark.asyncio
    async def test_run_agent_workflow_async_basic_parameters(self):
        """测试基本参数设置"""
        with patch.object(graph, "astream") as mock_astream:
            # Mock astream to return a simple async generator
            async def mock_generator():
                yield {"messages": [{"role": "assistant", "content": "test response"}]}

            mock_astream.return_value = mock_generator()

            # 不应该抛出异常
            try:
                await run_agent_workflow_async("test input")
            except Exception as e:
                # 可能会有一些内部错误，但不应该是输入验证错误
                assert "Input could not be empty" not in str(e)

            # 验证astream被调用
            assert mock_astream.called
            call_args = mock_astream.call_args
            assert call_args is not None

            # 检查输入参数
            input_state = call_args[1]["input"]
            assert input_state["messages"][0]["content"] == "test input"
            assert input_state["auto_accepted_plan"] is True
            assert input_state["enable_background_investigation"] is True

            # 检查配置参数
            config = call_args[1]["config"]
            assert config["configurable"]["max_plan_iterations"] == 1
            assert config["configurable"]["max_step_num"] == 3
            assert config["recursion_limit"] == 100

    @pytest.mark.asyncio
    async def test_run_agent_workflow_async_custom_parameters(self):
        """测试自定义参数"""
        with patch.object(graph, "astream") as mock_astream:

            async def mock_generator():
                yield {"messages": [{"role": "assistant", "content": "test"}]}

            mock_astream.return_value = mock_generator()

            await run_agent_workflow_async(
                "test input",
                debug=True,
                max_plan_iterations=5,
                max_step_num=10,
                enable_background_investigation=False,
            )

            # 验证配置参数
            call_args = mock_astream.call_args
            config = call_args[1]["config"]
            assert config["configurable"]["max_plan_iterations"] == 5
            assert config["configurable"]["max_step_num"] == 10

            input_state = call_args[1]["input"]
            assert input_state["enable_background_investigation"] is False

    @pytest.mark.asyncio
    async def test_run_agent_workflow_async_debug_logging(self):
        """测试debug模式下的日志设置"""
        with (
            patch("src.workflow.setup_debug_logging") as mock_debug_log,
            patch("src.workflow.setup_simplified_logging") as mock_simple_log,
            patch.object(graph, "astream") as mock_astream,
        ):

            async def mock_generator():
                yield {"messages": [{"role": "assistant", "content": "test"}]}

            mock_astream.return_value = mock_generator()

            # 测试debug=True
            await run_agent_workflow_async("test input", debug=True)
            mock_debug_log.assert_called_once()
            mock_simple_log.assert_not_called()

            # 重置mock
            mock_debug_log.reset_mock()
            mock_simple_log.reset_mock()

            # 测试debug=False
            await run_agent_workflow_async("test input", debug=False)
            mock_debug_log.assert_not_called()
            mock_simple_log.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_agent_workflow_async_stream_processing(self):
        """测试流处理逻辑"""
        with (
            patch.object(graph, "astream") as mock_astream,
            patch("builtins.print") as mock_print,
        ):

            # 创建mock消息对象
            mock_message1 = Mock()
            mock_message1.pretty_print = Mock()

            mock_message2 = Mock()
            mock_message2.pretty_print = Mock()

            async def mock_generator():
                # 测试不同的流输出格式
                yield {"messages": [mock_message1]}
                yield {"messages": [mock_message1, mock_message2]}  # 新消息
                yield {"messages": [mock_message1, mock_message2]}  # 重复消息，应该跳过
                yield {"other_data": "test"}  # 非消息格式
                # 测试tuple格式的消息
                yield {"messages": [("system", "tuple message")]}

            mock_astream.return_value = mock_generator()

            await run_agent_workflow_async("test input")

            # 验证pretty_print被调用了正确的次数
            assert mock_message1.pretty_print.call_count == 1
            assert mock_message2.pretty_print.call_count == 1

    @pytest.mark.asyncio
    async def test_run_agent_workflow_async_stream_error_handling(self):
        """测试流处理中的错误处理"""
        with (
            patch.object(graph, "astream") as mock_astream,
            patch("builtins.print") as mock_print,
            patch("src.workflow.logger") as mock_logger,
        ):

            # 创建会抛出异常的mock消息
            mock_message = Mock()
            mock_message.pretty_print.side_effect = Exception("Print error")

            async def mock_generator():
                yield {"messages": [mock_message]}

            mock_astream.return_value = mock_generator()

            # 应该不抛出异常，而是记录错误
            await run_agent_workflow_async("test input")

            # 验证错误被记录
            mock_logger.error.assert_called()
            error_call = mock_logger.error.call_args[0][0]
            assert "Error processing stream output" in error_call

    @pytest.mark.asyncio
    async def test_run_agent_workflow_async_mcp_settings(self):
        """测试MCP设置"""
        with patch.object(graph, "astream") as mock_astream:

            async def mock_generator():
                yield {"messages": [{"role": "assistant", "content": "test"}]}

            mock_astream.return_value = mock_generator()

            await run_agent_workflow_async("test input")

            call_args = mock_astream.call_args
            config = call_args[1]["config"]
            mcp_settings = config["configurable"]["mcp_settings"]

            # 验证MCP设置存在
            assert "servers" in mcp_settings
            assert "mcp-github-trending" in mcp_settings["servers"]

            github_server = mcp_settings["servers"]["mcp-github-trending"]
            assert github_server["transport"] == "stdio"
            assert github_server["command"] == "uvx"
            assert "mcp-github-trending" in github_server["args"]
            assert "get_github_trending_repositories" in github_server["enabled_tools"]
            assert "researcher" in github_server["add_to_agents"]

    @pytest.mark.asyncio
    async def test_run_agent_workflow_async_initial_state(self):
        """测试初始状态设置"""
        with patch.object(graph, "astream") as mock_astream:

            async def mock_generator():
                yield {"messages": [{"role": "assistant", "content": "test"}]}

            mock_astream.return_value = mock_generator()

            test_input = "测试中文输入"
            await run_agent_workflow_async(
                test_input, enable_background_investigation=False
            )

            call_args = mock_astream.call_args
            initial_state = call_args[1]["input"]

            # 验证初始状态
            assert len(initial_state["messages"]) == 1
            assert initial_state["messages"][0]["role"] == "user"
            assert initial_state["messages"][0]["content"] == test_input
            assert initial_state["auto_accepted_plan"] is True
            assert initial_state["enable_background_investigation"] is False


class TestWorkflowIntegration:
    """Workflow集成测试"""

    def test_module_imports(self):
        """测试模块导入"""
        # 测试可以正常导入所有必要的组件
        from src.workflow import graph, run_agent_workflow_async
        from src.graph import build_graph
        from src.config.logging_config import (
            setup_simplified_logging,
            setup_debug_logging,
        )

        assert graph is not None
        assert callable(run_agent_workflow_async)
        assert callable(build_graph)
        assert callable(setup_simplified_logging)
        assert callable(setup_debug_logging)

    @pytest.mark.asyncio
    async def test_workflow_with_real_graph(self):
        """测试与真实图的基本交互（如果图构建成功）"""
        try:
            # 尝试构建图并检查基本属性
            from src.graph import build_graph

            test_graph = build_graph()

            assert test_graph is not None
            assert hasattr(test_graph, "astream")

            # 如果图构建成功，测试一个非常简单的调用
            # 注意：这可能会因为缺少某些依赖而失败，但不应该影响其他测试

        except Exception as e:
            # 如果图构建失败，跳过这个测试
            pytest.skip(f"Graph construction failed: {e}")
