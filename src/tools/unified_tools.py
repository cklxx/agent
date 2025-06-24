# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT

"""
统一工具接口 - 集成所有优化后的工具，提供一致的API
"""

import logging
import functools
from typing import Any, Dict, List, Optional, Union, Callable
from langchain_core.tools import tool

from .middleware import (
    get_tool_middleware,
    ToolError,
    ToolSecurityError,
    ToolTimeoutError,
    ToolResourceError,
    CacheConfig,
    CachePolicy,
)
from .async_tools import get_async_tool_manager, run_tool_async, run_tool_sync
from .optimized_tools import (
    optimized_view_file,
    optimized_list_files,
    optimized_glob_search,
    optimized_grep_search,
    optimized_edit_file,
    get_path_resolver,
    get_resource_manager,
    get_optimization_stats,
    cleanup_all_optimized_resources,
)
from .optimized_bash_tool import (
    optimized_bash_command,
    list_background_processes,
    stop_background_process,
    get_process_logs,
    cleanup_all_processes,
)

logger = logging.getLogger(__name__)


class ToolExecutionError(Exception):
    """工具执行错误基类 - 统一错误接口"""

    def __init__(
        self,
        message: str,
        tool_name: str = "",
        error_code: str = "TOOL_ERROR",
        original_error: Optional[Exception] = None,
        suggestions: Optional[List[str]] = None,
    ):
        super().__init__(message)
        self.tool_name = tool_name
        self.error_code = error_code
        self.original_error = original_error
        self.suggestions = suggestions or []

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "error_type": self.__class__.__name__,
            "message": str(self),
            "tool_name": self.tool_name,
            "error_code": self.error_code,
            "original_error": str(self.original_error) if self.original_error else None,
            "suggestions": self.suggestions,
        }

    def __str__(self) -> str:
        error_msg = super().__str__()
        if self.tool_name:
            error_msg = f"[{self.tool_name}] {error_msg}"
        if self.suggestions:
            error_msg += f"\n建议: {'; '.join(self.suggestions)}"
        return error_msg


def unified_error_handler(func: Callable) -> Callable:
    """统一错误处理装饰器"""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        tool_name = getattr(func, "__name__", "unknown_tool")

        try:
            return func(*args, **kwargs)

        except ToolSecurityError as e:
            raise ToolExecutionError(
                message=str(e),
                tool_name=tool_name,
                error_code="SECURITY_ERROR",
                original_error=e,
                suggestions=["检查命令是否包含禁用的操作", "使用推荐的替代工具"],
            )

        except ToolTimeoutError as e:
            raise ToolExecutionError(
                message=str(e),
                tool_name=tool_name,
                error_code="TIMEOUT_ERROR",
                original_error=e,
                suggestions=["增加超时时间", "优化命令执行效率", "检查网络连接"],
            )

        except ToolResourceError as e:
            raise ToolExecutionError(
                message=str(e),
                tool_name=tool_name,
                error_code="RESOURCE_ERROR",
                original_error=e,
                suggestions=["检查磁盘空间", "检查内存使用", "清理临时文件"],
            )

        except ToolError as e:
            raise ToolExecutionError(
                message=str(e),
                tool_name=tool_name,
                error_code="TOOL_ERROR",
                original_error=e,
                suggestions=["检查工具参数", "查看详细日志", "重试操作"],
            )

        except FileNotFoundError as e:
            raise ToolExecutionError(
                message=f"文件或目录不存在: {str(e)}",
                tool_name=tool_name,
                error_code="FILE_NOT_FOUND",
                original_error=e,
                suggestions=["检查文件路径是否正确", "确认文件是否存在", "检查权限"],
            )

        except PermissionError as e:
            raise ToolExecutionError(
                message=f"权限不足: {str(e)}",
                tool_name=tool_name,
                error_code="PERMISSION_ERROR",
                original_error=e,
                suggestions=["检查文件权限", "使用管理员权限", "更改文件所有者"],
            )

        except Exception as e:
            raise ToolExecutionError(
                message=f"未知错误: {str(e)}",
                tool_name=tool_name,
                error_code="UNKNOWN_ERROR",
                original_error=e,
                suggestions=["查看详细错误日志", "重试操作", "联系技术支持"],
            )

    return wrapper


class UnifiedToolManager:
    """统一工具管理器"""

    def __init__(
        self,
        workspace: Optional[str] = None,
        cache_config: Optional[CacheConfig] = None,
        enable_metrics: bool = True,
    ):
        self.workspace = workspace
        self.cache_config = cache_config or CacheConfig(
            policy=CachePolicy.INTELLIGENT, ttl=300, max_size=1000
        )
        self.enable_metrics = enable_metrics

        # 初始化组件
        self.middleware = get_tool_middleware(
            cache_config=self.cache_config, enable_metrics=enable_metrics
        )
        self.async_manager = get_async_tool_manager()
        self.path_resolver = get_path_resolver()
        self.resource_manager = get_resource_manager()

        logger.info(f"统一工具管理器初始化完成 - workspace: {workspace}")

    # 文件系统工具
    @unified_error_handler
    def view_file(
        self, file_path: str, offset: Optional[int] = None, limit: Optional[int] = None
    ) -> str:
        """查看文件内容"""
        return optimized_view_file(file_path, self.workspace, offset, limit)

    @unified_error_handler
    def list_files(self, path: str) -> str:
        """列出目录内容"""
        return optimized_list_files(path, self.workspace)

    @unified_error_handler
    def glob_search(self, pattern: str, path: Optional[str] = None) -> str:
        """glob模式搜索"""
        return optimized_glob_search(pattern, path, self.workspace)

    @unified_error_handler
    def grep_search(
        self, pattern: str, path: Optional[str] = None, include: Optional[str] = None
    ) -> str:
        """文本内容搜索"""
        return optimized_grep_search(pattern, path, include, self.workspace)

    @unified_error_handler
    def edit_file(self, file_path: str, old_string: str, new_string: str) -> str:
        """编辑文件"""
        return optimized_edit_file(file_path, old_string, new_string, self.workspace)

    # 命令执行工具
    @unified_error_handler
    def bash_command(
        self,
        command: str,
        timeout: Optional[int] = None,
        run_in_background: bool = False,
    ) -> str:
        """执行bash命令"""
        return optimized_bash_command(
            command=command,
            timeout=timeout,
            working_directory=self.workspace,
            run_in_background=run_in_background,
        )

    @unified_error_handler
    def list_processes(self) -> str:
        """列出后台进程"""
        return list_background_processes()

    @unified_error_handler
    def stop_process(self, process_id: str, force: bool = False) -> str:
        """停止后台进程"""
        return stop_background_process(process_id, force)

    @unified_error_handler
    def get_logs(self, process_id: str, lines: int = 50) -> str:
        """获取进程日志"""
        return get_process_logs(process_id, lines)

    # 异步工具接口
    async def view_file_async(
        self, file_path: str, offset: Optional[int] = None, limit: Optional[int] = None
    ) -> str:
        """异步查看文件"""
        return await run_tool_async(
            optimized_view_file, file_path, self.workspace, offset, limit
        )

    async def bash_command_async(
        self,
        command: str,
        timeout: Optional[int] = None,
        run_in_background: bool = False,
    ) -> str:
        """异步执行bash命令"""
        return await run_tool_async(
            optimized_bash_command,
            command=command,
            timeout=timeout,
            working_directory=self.workspace,
            run_in_background=run_in_background,
        )

    # 批量操作
    async def batch_operations_async(
        self, operations: List[Dict[str, Any]]
    ) -> List[Any]:
        """批量异步操作"""
        tool_calls = []

        for op in operations:
            op_type = op.get("type")
            args = op.get("args", ())
            kwargs = op.get("kwargs", {})

            if op_type == "view_file":
                tool_calls.append(
                    {
                        "func": lambda *a, **k: self.view_file(*a, **k),
                        "args": args,
                        "kwargs": kwargs,
                        "name": "view_file",
                    }
                )
            elif op_type == "bash_command":
                tool_calls.append(
                    {
                        "func": lambda *a, **k: self.bash_command(*a, **k),
                        "args": args,
                        "kwargs": kwargs,
                        "name": "bash_command",
                    }
                )
            # 可以添加更多操作类型

        return await self.async_manager.execute_batch_async(tool_calls)

    # 管理功能
    def get_stats(self) -> Dict[str, Any]:
        """获取工具使用统计"""
        return {
            "optimization_stats": get_optimization_stats(),
            "middleware_metrics": self.middleware.get_metrics(),
            "async_manager_info": {
                "max_workers": self.async_manager.max_workers,
                "active_tasks": len(self.async_manager._active_tasks),
            },
        }

    def clear_cache(self, tool_name: Optional[str] = None):
        """清理缓存"""
        self.middleware.cache.clear(tool_name)
        logger.info(f"已清理缓存: {tool_name or '全部'}")

    def cleanup(self):
        """清理所有资源"""
        try:
            # 清理进程
            cleanup_all_processes()

            # 清理优化资源
            cleanup_all_optimized_resources()

            # 清理中间件
            self.middleware.cleanup()

            # 停止异步管理器
            self.async_manager.shutdown()

            logger.info("统一工具管理器资源清理完成")

        except Exception as e:
            logger.error(f"清理资源时出错: {e}")


# 全局工具管理器实例
_global_tool_manager: Optional[UnifiedToolManager] = None


def get_unified_tool_manager(
    workspace: Optional[str] = None,
    cache_config: Optional[CacheConfig] = None,
    enable_metrics: bool = True,
) -> UnifiedToolManager:
    """获取统一工具管理器"""
    global _global_tool_manager

    if _global_tool_manager is None or _global_tool_manager.workspace != workspace:
        _global_tool_manager = UnifiedToolManager(
            workspace=workspace,
            cache_config=cache_config,
            enable_metrics=enable_metrics,
        )

    return _global_tool_manager


# LangChain工具包装器
@tool
def unified_view_file(
    file_path: str,
    workspace: Optional[str] = None,
    offset: Optional[int] = None,
    limit: Optional[int] = None,
) -> str:
    """
    统一文件查看工具 - 支持缓存和错误处理

    Args:
        file_path: 文件路径
        workspace: 工作区路径
        offset: 起始行号
        limit: 读取行数
    """
    manager = get_unified_tool_manager(workspace)
    return manager.view_file(file_path, offset, limit)


@tool
def unified_bash_command(
    command: str,
    workspace: Optional[str] = None,
    timeout: Optional[int] = None,
    run_in_background: bool = False,
) -> str:
    """
    统一bash命令工具 - 支持进程管理和错误处理

    Args:
        command: shell命令
        workspace: 工作区路径
        timeout: 超时时间（毫秒）
        run_in_background: 是否后台运行
    """
    manager = get_unified_tool_manager(workspace)
    return manager.bash_command(command, timeout, run_in_background)


@tool
def unified_list_files(path: str, workspace: Optional[str] = None) -> str:
    """
    统一文件列表工具 - 支持缓存和路径优化

    Args:
        path: 目录路径
        workspace: 工作区路径
    """
    manager = get_unified_tool_manager(workspace)
    return manager.list_files(path)


@tool
def unified_glob_search(
    pattern: str, path: Optional[str] = None, workspace: Optional[str] = None
) -> str:
    """
    统一glob搜索工具 - 支持缓存和模式优化

    Args:
        pattern: 搜索模式
        path: 搜索路径
        workspace: 工作区路径
    """
    manager = get_unified_tool_manager(workspace)
    return manager.glob_search(pattern, path)


@tool
def unified_grep_search(
    pattern: str,
    path: Optional[str] = None,
    include: Optional[str] = None,
    workspace: Optional[str] = None,
) -> str:
    """
    统一grep搜索工具 - 支持缓存和内容检索

    Args:
        pattern: 搜索模式
        path: 搜索路径
        include: 文件过滤
        workspace: 工作区路径
    """
    manager = get_unified_tool_manager(workspace)
    return manager.grep_search(pattern, path, include)


@tool
def get_tool_stats(workspace: Optional[str] = None) -> str:
    """
    获取工具使用统计

    Args:
        workspace: 工作区路径
    """
    manager = get_unified_tool_manager(workspace)
    stats = manager.get_stats()

    # 格式化输出
    output = "## 工具使用统计\n\n"

    # 中间件指标
    middleware_metrics = stats.get("middleware_metrics", {})
    if middleware_metrics:
        output += "### 中间件指标\n"
        for tool_name, metrics in middleware_metrics.items():
            output += f"- **{tool_name}**:\n"
            output += f"  - 调用次数: {metrics.call_count}\n"
            output += f"  - 平均耗时: {metrics.average_time:.3f}s\n"
            output += f"  - 错误次数: {metrics.error_count}\n"
            output += f"  - 缓存命中率: {metrics.cache_hit_rate:.2%}\n"

    # 优化统计
    opt_stats = stats.get("optimization_stats", {})
    if opt_stats:
        output += "\n### 优化统计\n"
        cache_stats = opt_stats.get("path_cache_stats", {})
        output += f"- 路径缓存大小: {cache_stats.get('cache_size', 0)}\n"
        output += f"- 活跃进程: {len(opt_stats.get('active_processes', {}))}\n"

    return output


def cleanup_unified_tools():
    """清理统一工具资源"""
    global _global_tool_manager
    if _global_tool_manager:
        _global_tool_manager.cleanup()
        _global_tool_manager = None


# 导出统一工具
__all__ = [
    "UnifiedToolManager",
    "get_unified_tool_manager",
    "ToolExecutionError",
    "unified_view_file",
    "unified_bash_command",
    "unified_list_files",
    "unified_glob_search",
    "unified_grep_search",
    "get_tool_stats",
    "cleanup_unified_tools",
]
