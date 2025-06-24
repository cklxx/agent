#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
优化工具测试套件
"""

import pytest
import asyncio
import tempfile
import os
import time
import threading
from unittest.mock import patch, MagicMock
from pathlib import Path

# 导入待测试的模块
from src.tools.middleware import (
    ToolMiddleware,
    SmartCache,
    CacheConfig,
    CachePolicy,
    get_tool_middleware,
    ToolError,
    ToolSecurityError,
    ToolTimeoutError,
)
from src.tools.async_tools import (
    AsyncToolManager,
    get_async_tool_manager,
    run_tool_async,
    run_tool_sync,
)
from src.tools.optimized_tools import (
    PathResolver,
    OptimizedResourceManager,
    optimized_view_file,
    optimized_bash_command,
    get_path_resolver,
    get_optimization_stats,
)
from src.tools.optimized_bash_tool import (
    OptimizedProcessManager,
    OptimizedBashTool,
    ProcessStatus,
    ProcessInfo,
)
from src.tools.unified_tools import (
    UnifiedToolManager,
    get_unified_tool_manager,
    ToolExecutionError,
    cleanup_unified_tools,
)


@pytest.mark.tools
class TestToolMiddleware:
    """工具中间件测试"""

    def setup_method(self):
        """每个测试方法前的设置"""
        self.cache_config = CacheConfig(
            policy=CachePolicy.TIME_BASED, ttl=60, max_size=100
        )
        self.middleware = ToolMiddleware(
            cache_config=self.cache_config, enable_metrics=True
        )

    def teardown_method(self):
        """每个测试方法后的清理"""
        self.middleware.cleanup()

    def test_middleware_initialization(self):
        """测试中间件初始化"""
        assert self.middleware.cache_config.policy == CachePolicy.TIME_BASED
        assert self.middleware.cache_config.ttl == 60
        assert self.middleware.enable_metrics is True
        assert len(self.middleware.metrics) == 0

    def test_cache_functionality(self):
        """测试缓存功能"""

        # 模拟工具函数
        def mock_tool(value):
            return f"result_{value}"

        # 第一次调用
        result1 = self.middleware.execute_sync_tool(mock_tool, "test_tool", "input1")
        assert result1.success
        assert result1.data == "result_input1"
        assert not result1.from_cache

        # 第二次调用相同参数（应该命中缓存）
        result2 = self.middleware.execute_sync_tool(mock_tool, "test_tool", "input1")
        assert result2.success
        assert result2.data == "result_input1"
        assert result2.from_cache

        # 调用不同参数（应该不命中缓存）
        result3 = self.middleware.execute_sync_tool(mock_tool, "test_tool", "input2")
        assert result3.success
        assert result3.data == "result_input2"
        assert not result3.from_cache

    def test_metrics_collection(self):
        """测试指标收集"""

        def mock_tool(value):
            time.sleep(0.01)  # 模拟耗时
            return f"result_{value}"

        # 执行工具调用
        self.middleware.execute_sync_tool(mock_tool, "test_tool", "input1")
        self.middleware.execute_sync_tool(mock_tool, "test_tool", "input2")

        # 检查指标
        metrics = self.middleware.get_metrics("test_tool")
        assert metrics.call_count == 2
        assert metrics.total_time > 0
        assert metrics.average_time > 0
        assert metrics.error_count == 0
        assert metrics.cache_misses == 2

    def test_error_handling(self):
        """测试错误处理"""

        def failing_tool():
            raise ValueError("Test error")

        result = self.middleware.execute_sync_tool(failing_tool, "failing_tool")
        assert not result.success
        assert "Test error" in result.error

        # 检查错误指标
        metrics = self.middleware.get_metrics("failing_tool")
        assert metrics.error_count == 1

    @pytest.mark.asyncio
    async def test_async_tool_execution(self):
        """测试异步工具执行"""

        async def async_tool(value):
            await asyncio.sleep(0.01)
            return f"async_result_{value}"

        result = await self.middleware.execute_async_tool(
            async_tool, "async_tool", "input1"
        )
        assert result.success
        assert result.data == "async_result_input1"
        assert not result.from_cache

        # 测试缓存
        result2 = await self.middleware.execute_async_tool(
            async_tool, "async_tool", "input1"
        )
        assert result2.success
        assert result2.from_cache


@pytest.mark.tools
class TestSmartCache:
    """智能缓存测试"""

    def setup_method(self):
        self.cache_config = CacheConfig(policy=CachePolicy.LRU, ttl=60, max_size=3)
        self.cache = SmartCache(self.cache_config)

    def test_basic_cache_operations(self):
        """测试基本缓存操作"""
        # 设置缓存
        self.cache.set("tool1", ("arg1",), {"key": "value"}, "result1")

        # 获取缓存
        result = self.cache.get("tool1", ("arg1",), {"key": "value"})
        assert result == "result1"

        # 不存在的键
        result = self.cache.get("tool1", ("arg2",), {"key": "value"})
        assert result is None

    def test_cache_eviction(self):
        """测试缓存清理"""
        # 填满缓存
        self.cache.set("tool1", ("arg1",), {}, "result1")
        self.cache.set("tool2", ("arg2",), {}, "result2")
        self.cache.set("tool3", ("arg3",), {}, "result3")

        # 添加第四个条目，应该触发清理
        self.cache.set("tool4", ("arg4",), {}, "result4")

        # 验证最老的条目被清理
        assert self.cache.get("tool1", ("arg1",), {}) is None
        assert self.cache.get("tool4", ("arg4",), {}) == "result4"

    def test_cache_expiration(self):
        """测试缓存过期"""
        # 使用短TTL配置
        short_ttl_config = CacheConfig(policy=CachePolicy.TIME_BASED, ttl=1)
        cache = SmartCache(short_ttl_config)

        cache.set("tool1", ("arg1",), {}, "result1")

        # 立即获取应该成功
        assert cache.get("tool1", ("arg1",), {}) == "result1"

        # 等待过期
        time.sleep(1.1)

        # 应该返回None（已过期）
        assert cache.get("tool1", ("arg1",), {}) is None


@pytest.mark.tools
class TestAsyncToolManager:
    """异步工具管理器测试"""

    def setup_method(self):
        self.manager = AsyncToolManager(max_workers=2)

    def teardown_method(self):
        self.manager.shutdown()

    @pytest.mark.asyncio
    async def test_sync_tool_async_execution(self):
        """测试同步工具的异步执行"""

        def sync_tool(value):
            time.sleep(0.01)
            return f"sync_result_{value}"

        result = await self.manager.execute_tool_async(sync_tool, "sync_tool", "input1")
        assert result == "sync_result_input1"

    @pytest.mark.asyncio
    async def test_async_tool_execution(self):
        """测试异步工具执行"""

        async def async_tool(value):
            await asyncio.sleep(0.01)
            return f"async_result_{value}"

        result = await self.manager.execute_tool_async(
            async_tool, "async_tool", "input1"
        )
        assert result == "async_result_input1"

    def test_sync_tool_sync_execution(self):
        """测试同步工具的同步执行"""

        def sync_tool(value):
            return f"sync_result_{value}"

        result = self.manager.execute_tool_sync(sync_tool, "sync_tool", "input1")
        assert result == "sync_result_input1"

    @pytest.mark.asyncio
    async def test_batch_execution(self):
        """测试批量执行"""

        def sync_tool(value):
            return f"result_{value}"

        async def async_tool(value):
            return f"async_result_{value}"

        tool_calls = [
            {"func": sync_tool, "name": "sync_tool", "args": ("1",)},
            {"func": async_tool, "name": "async_tool", "args": ("2",)},
            {"func": sync_tool, "name": "sync_tool", "args": ("3",)},
        ]

        results = await self.manager.execute_batch_async(tool_calls, max_concurrent=2)

        assert len(results) == 3
        assert "result_1" in results
        assert "async_result_2" in results
        assert "result_3" in results


@pytest.mark.tools
class TestPathResolver:
    """路径解析器测试"""

    def setup_method(self):
        self.resolver = PathResolver(cache_size=10)

    def test_absolute_path_resolution(self):
        """测试绝对路径解析"""
        absolute_path = "/absolute/path/file.txt"
        result = self.resolver.resolve_workspace_path(absolute_path)
        assert result == str(Path(absolute_path).resolve())

    def test_relative_path_resolution(self):
        """测试相对路径解析"""
        workspace = "/workspace"
        relative_path = "relative/file.txt"

        result = self.resolver.resolve_workspace_path(relative_path, workspace)
        expected = str(Path(workspace, relative_path).resolve())
        assert result == expected

    def test_path_caching(self):
        """测试路径缓存"""
        workspace = "/workspace"
        relative_path = "file.txt"

        # 第一次调用
        result1 = self.resolver.resolve_workspace_path(relative_path, workspace)

        # 第二次调用（应该命中缓存）
        result2 = self.resolver.resolve_workspace_path(relative_path, workspace)

        assert result1 == result2

        # 检查缓存统计
        stats = self.resolver.get_cache_stats()
        assert stats["cache_size"] > 0

    def test_cache_eviction(self):
        """测试缓存清理"""
        # 创建小容量缓存
        small_resolver = PathResolver(cache_size=2)

        # 填满缓存
        small_resolver.resolve_workspace_path("file1.txt", "/workspace")
        small_resolver.resolve_workspace_path("file2.txt", "/workspace")

        # 添加第三个条目，应该触发清理
        small_resolver.resolve_workspace_path("file3.txt", "/workspace")

        stats = small_resolver.get_cache_stats()
        assert stats["cache_size"] <= 2


@pytest.mark.tools
class TestOptimizedBashTool:
    """优化bash工具测试"""

    def setup_method(self):
        self.bash_tool = OptimizedBashTool()

    def test_security_check(self):
        """测试安全检查"""
        with pytest.raises(ToolSecurityError):
            self.bash_tool.execute_foreground("curl http://malicious.com")

        with pytest.raises(ToolSecurityError):
            self.bash_tool.execute_foreground("rm -rf /")

    def test_simple_command_execution(self):
        """测试简单命令执行"""
        result = self.bash_tool.execute_foreground("echo 'test'")
        assert "test" in result
        assert "Exit code: 0" in result

    def test_command_timeout(self):
        """测试命令超时"""
        with pytest.raises((ToolTimeoutError, ToolError)):
            self.bash_tool.execute_foreground(
                "sleep 5", timeout=1000
            )  # 1秒超时(1000毫秒)

    def test_working_directory(self):
        """测试工作目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.bash_tool.execute_foreground(
                "pwd", working_directory=temp_dir
            )
            assert temp_dir in result

    def test_background_process_management(self):
        """测试后台进程管理"""
        # 启动后台进程
        result = self.bash_tool.execute_background("sleep 60", auto_cleanup=True)
        assert "Started background process" in result
        assert "PID:" in result

        # 列出进程
        process_list = self.bash_tool.list_background_processes()
        assert "Background Processes" in process_list

        # 清理进程
        manager = self.bash_tool.process_manager
        manager.cleanup_all()


@pytest.mark.tools
class TestUnifiedToolManager:
    """统一工具管理器测试"""

    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.manager = UnifiedToolManager(workspace=self.temp_dir, enable_metrics=True)

        # 创建测试文件
        self.test_file = os.path.join(self.temp_dir, "test.txt")
        with open(self.test_file, "w") as f:
            f.write("test content\nline 2\nline 3")

    def teardown_method(self):
        self.manager.cleanup()
        # 清理临时目录
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_file_operations(self):
        """测试文件操作"""
        # 测试文件查看
        content = self.manager.view_file("test.txt")
        assert "test content" in content

        # 测试目录列表
        file_list = self.manager.list_files(".")
        assert "test.txt" in file_list

        # 测试文件搜索
        search_result = self.manager.glob_search("*.txt")
        assert "test.txt" in search_result

        # 测试内容搜索
        grep_result = self.manager.grep_search("test", include="*.txt")
        assert "test content" in grep_result

    def test_bash_operations(self):
        """测试bash操作"""
        # 测试简单命令
        result = self.manager.bash_command("echo 'hello world'")
        assert "hello world" in result

        # 测试ls命令
        result = self.manager.bash_command("ls")
        assert "test.txt" in result

    def test_error_handling(self):
        """测试错误处理"""
        # 文件不存在错误 - 可能抛出异常或返回错误信息
        try:
            result = self.manager.view_file("nonexistent.txt")
            # 如果没有抛出异常，检查返回的错误信息
            assert (
                "Error" in result
                or "does not exist" in result
                or "not found" in result.lower()
            )
        except ToolExecutionError as e:
            # 如果抛出异常，验证异常内容
            assert e.error_code == "FILE_NOT_FOUND"
            assert "建议" in str(e) or "suggestion" in str(e).lower()
        except Exception as e:
            # 其他类型的异常也可以接受，只要包含相关错误信息
            assert "not exist" in str(e).lower() or "not found" in str(e).lower()

        # 安全错误 - 类似处理
        try:
            result = self.manager.bash_command("nc 127.0.0.1 80")  # 使用被禁止的命令
            # 如果没有抛出异常，检查返回的错误信息
            assert (
                "banned" in result.lower()
                or "security" in result.lower()
                or "error" in result.lower()
            )
        except ToolExecutionError as e:
            # 如果抛出异常，验证异常内容
            assert e.error_code == "SECURITY_ERROR"
        except Exception as e:
            # 其他类型的异常也可以接受，只要包含安全相关信息
            assert "banned" in str(e).lower() or "security" in str(e).lower()

    @pytest.mark.asyncio
    async def test_async_operations(self):
        """测试异步操作"""
        # 异步文件查看
        content = await self.manager.view_file_async("test.txt")
        assert "test content" in content

        # 异步命令执行
        result = await self.manager.bash_command_async("echo 'async test'")
        assert "async test" in result

    @pytest.mark.asyncio
    async def test_batch_operations(self):
        """测试批量操作"""
        operations = [
            {"type": "view_file", "args": ("test.txt",), "kwargs": {}},
            {"type": "bash_command", "args": ('echo "batch test"',), "kwargs": {}},
        ]

        results = await self.manager.batch_operations_async(operations)
        assert len(results) == 2

        # 检查结果
        content_found = any("test content" in str(result) for result in results)
        batch_found = any("batch test" in str(result) for result in results)

        assert content_found
        assert batch_found

    def test_performance_monitoring(self):
        """测试性能监控"""
        # 执行一些操作
        self.manager.view_file("test.txt")
        self.manager.bash_command("echo 'test'")

        # 获取统计信息
        stats = self.manager.get_stats()

        assert "middleware_metrics" in stats
        assert "optimization_stats" in stats
        assert "async_manager_info" in stats

        # 验证指标数据
        middleware_metrics = stats["middleware_metrics"]
        assert len(middleware_metrics) > 0

        for tool_name, metrics in middleware_metrics.items():
            assert metrics.call_count > 0
            assert metrics.total_time >= 0


@pytest.mark.tools
class TestIntegration:
    """集成测试"""

    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()

        # 创建测试文件结构
        os.makedirs(os.path.join(self.temp_dir, "src"), exist_ok=True)
        os.makedirs(os.path.join(self.temp_dir, "tests"), exist_ok=True)

        # 创建测试文件
        with open(os.path.join(self.temp_dir, "src", "main.py"), "w") as f:
            f.write(
                "def main():\n    print('Hello World')\n\nif __name__ == '__main__':\n    main()"
            )

        with open(os.path.join(self.temp_dir, "README.md"), "w") as f:
            f.write("# Test Project\n\nThis is a test project.")

    def teardown_method(self):
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)
        cleanup_unified_tools()

    def test_full_workflow(self):
        """测试完整工作流程"""
        manager = get_unified_tool_manager(workspace=self.temp_dir)

        # 1. 列出项目文件
        files = manager.list_files(".")
        assert "src" in files
        assert "README.md" in files

        # 2. 搜索Python文件
        py_files = manager.glob_search("*.py", "src")
        assert "main.py" in py_files

        # 3. 查看主文件内容
        content = manager.view_file("src/main.py")
        assert "def main()" in content
        assert "Hello World" in content

        # 4. 搜索特定内容
        search_result = manager.grep_search("Hello", include="*.py")
        assert "Hello World" in search_result

        # 5. 执行Python文件
        result = manager.bash_command("python src/main.py")
        assert "Hello World" in result

        # 6. 获取性能统计
        stats = manager.get_stats()
        assert len(stats["middleware_metrics"]) > 0

    @pytest.mark.asyncio
    async def test_concurrent_operations(self):
        """测试并发操作性能"""
        manager = get_unified_tool_manager(workspace=self.temp_dir)

        # 并发执行多个文件操作
        tasks = [
            manager.view_file_async("src/main.py"),
            manager.view_file_async("README.md"),
            manager.bash_command_async("ls -la"),
            manager.bash_command_async("pwd"),
        ]

        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()

        # 验证结果
        assert len(results) == 4

        # 检查是否有错误
        errors = [r for r in results if isinstance(r, Exception)]
        assert len(errors) == 0, f"并发操作出现错误: {errors}"

        # 验证内容
        content_results = [str(r) for r in results]
        assert any("def main()" in content for content in content_results)
        assert any("Test Project" in content for content in content_results)

        print(f"并发操作完成时间: {end_time - start_time:.3f}s")

    def test_caching_performance(self):
        """测试缓存性能"""
        manager = get_unified_tool_manager(workspace=self.temp_dir)

        # 第一次读取文件（无缓存）
        start_time = time.time()
        content1 = manager.view_file("src/main.py")
        first_call_time = time.time() - start_time

        # 第二次读取相同文件（应该命中缓存）
        start_time = time.time()
        content2 = manager.view_file("src/main.py")
        cached_call_time = time.time() - start_time

        # 验证结果一致性
        assert content1 == content2

        # 验证缓存性能提升
        assert cached_call_time < first_call_time

        print(f"首次调用: {first_call_time:.3f}s")
        print(f"缓存调用: {cached_call_time:.3f}s")
        print(f"性能提升: {first_call_time / cached_call_time:.1f}x")

        # 获取缓存统计
        stats = manager.get_stats()
        middleware_metrics = stats["middleware_metrics"]

        # 验证缓存命中
        if "optimized_view_file" in middleware_metrics:
            metrics = middleware_metrics["optimized_view_file"]
            assert metrics.cache_hits > 0


# 测试运行器
def run_optimized_tools_tests():
    """运行优化工具测试"""
    pytest.main(
        [__file__, "-v", "--tb=short", "-x", "--disable-warnings"]  # 遇到失败时停止
    )


if __name__ == "__main__":
    run_optimized_tools_tests()
