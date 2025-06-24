# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT

"""
优化的工具实现 - 集成中间件、缓存和路径优化
"""

import os
import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from functools import lru_cache
import threading

from .middleware import get_tool_middleware, CacheConfig, CachePolicy, tool_middleware
from .async_tools import async_tool_wrapper, sync_tool_wrapper

logger = logging.getLogger(__name__)


class PathResolver:
    """优化的路径解析器，带缓存功能"""

    def __init__(self, cache_size: int = 1000):
        self.cache_size = cache_size
        self._cache: Dict[tuple, str] = {}
        self._cache_lock = threading.RLock()
        self._access_order: List[tuple] = []

    def _evict_cache(self):
        """LRU缓存清理"""
        if len(self._cache) >= self.cache_size:
            # 移除最久未使用的条目
            oldest_key = self._access_order.pop(0)
            self._cache.pop(oldest_key, None)

    def resolve_workspace_path(
        self, file_path: str, workspace: Optional[str] = None
    ) -> str:
        """
        优化的工作区路径解析，带缓存

        Args:
            file_path: 文件路径
            workspace: 工作区路径

        Returns:
            解析后的绝对路径
        """
        # 生成缓存键
        cache_key = (file_path, workspace)

        with self._cache_lock:
            # 检查缓存
            if cache_key in self._cache:
                # 更新访问顺序
                self._access_order.remove(cache_key)
                self._access_order.append(cache_key)
                return self._cache[cache_key]

            # 执行路径解析
            if not workspace:
                resolved_path = file_path
            elif os.path.isabs(file_path):
                resolved_path = file_path
            else:
                resolved_path = str(Path(workspace) / file_path)

            # 标准化路径
            resolved_path = str(Path(resolved_path).resolve())

            # 缓存结果
            self._evict_cache()
            self._cache[cache_key] = resolved_path
            self._access_order.append(cache_key)

            return resolved_path

    def clear_cache(self):
        """清理路径缓存"""
        with self._cache_lock:
            self._cache.clear()
            self._access_order.clear()

    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self._cache_lock:
            return {
                "cache_size": len(self._cache),
                "max_size": self.cache_size,
                "hit_rate": len(self._cache) / max(len(self._access_order), 1),
            }


class OptimizedResourceManager:
    """优化的资源管理器"""

    def __init__(self):
        self._resources: Dict[str, Any] = {}
        self._cleanup_callbacks: Dict[str, callable] = {}
        self._resource_lock = threading.RLock()
        self._active_processes: Dict[str, Dict] = {}

    def register_resource(
        self,
        resource_id: str,
        resource: Any,
        cleanup_callback: Optional[callable] = None,
    ):
        """注册资源"""
        with self._resource_lock:
            self._resources[resource_id] = resource
            if cleanup_callback:
                self._cleanup_callbacks[resource_id] = cleanup_callback

    def register_process(self, process_id: str, process_info: Dict[str, Any]):
        """注册进程信息"""
        with self._resource_lock:
            self._active_processes[process_id] = process_info

    def cleanup_resource(self, resource_id: str) -> bool:
        """清理特定资源"""
        with self._resource_lock:
            if resource_id not in self._resources:
                return False

            try:
                resource = self._resources[resource_id]
                cleanup_callback = self._cleanup_callbacks.get(resource_id)

                if cleanup_callback:
                    cleanup_callback()
                elif hasattr(resource, "close"):
                    resource.close()
                elif hasattr(resource, "cleanup"):
                    resource.cleanup()

                del self._resources[resource_id]
                self._cleanup_callbacks.pop(resource_id, None)
                return True

            except Exception as e:
                logger.error(f"清理资源 {resource_id} 失败: {e}")
                return False

    def cleanup_all_resources(self):
        """清理所有资源"""
        with self._resource_lock:
            for resource_id in list(self._resources.keys()):
                self.cleanup_resource(resource_id)

    def get_active_processes(self) -> Dict[str, Dict]:
        """获取活跃进程列表"""
        with self._resource_lock:
            return self._active_processes.copy()

    def cleanup_process(self, process_id: str) -> bool:
        """清理特定进程"""
        with self._resource_lock:
            if process_id not in self._active_processes:
                return False

            try:
                process_info = self._active_processes[process_id]
                pid = process_info.get("pid")

                if pid:
                    import subprocess

                    # 尝试优雅关闭
                    subprocess.run(f"kill {pid}", shell=True, capture_output=True)

                    # 检查是否还在运行
                    import time

                    time.sleep(1)
                    result = subprocess.run(
                        f"ps -p {pid}", shell=True, capture_output=True
                    )
                    if result.returncode == 0:
                        # 强制关闭
                        subprocess.run(
                            f"kill -9 {pid}", shell=True, capture_output=True
                        )

                del self._active_processes[process_id]
                return True

            except Exception as e:
                logger.error(f"清理进程 {process_id} 失败: {e}")
                return False


# 全局实例
_global_path_resolver: Optional[PathResolver] = None
_global_resource_manager: Optional[OptimizedResourceManager] = None
_resolver_lock = threading.Lock()
_manager_lock = threading.Lock()


def get_path_resolver() -> PathResolver:
    """获取全局路径解析器"""
    global _global_path_resolver
    if _global_path_resolver is None:
        with _resolver_lock:
            if _global_path_resolver is None:
                _global_path_resolver = PathResolver()
    return _global_path_resolver


def get_resource_manager() -> OptimizedResourceManager:
    """获取全局资源管理器"""
    global _global_resource_manager
    if _global_resource_manager is None:
        with _manager_lock:
            if _global_resource_manager is None:
                _global_resource_manager = OptimizedResourceManager()
    return _global_resource_manager


# 优化的工具实现
@tool_middleware(
    tool_name="optimized_view_file", cache_policy=CachePolicy.INTELLIGENT, cache_ttl=600
)
def optimized_view_file(
    file_path: str,
    workspace: Optional[str] = None,
    offset: Optional[int] = None,
    limit: Optional[int] = None,
) -> str:
    """
    优化的文件查看工具

    Args:
        file_path: 文件路径
        workspace: 工作区路径
        offset: 起始行号
        limit: 读取行数限制
    """
    from .file_system_tools import view_file as view_file_raw

    # 使用优化的路径解析
    resolver = get_path_resolver()
    resolved_path = resolver.resolve_workspace_path(file_path, workspace)

    # 调用原始工具
    return view_file_raw.func(resolved_path, offset, limit)


@tool_middleware(
    tool_name="optimized_list_files", cache_policy=CachePolicy.TIME_BASED, cache_ttl=120
)
def optimized_list_files(path: str, workspace: Optional[str] = None) -> str:
    """
    优化的文件列表工具

    Args:
        path: 目录路径
        workspace: 工作区路径
    """
    from .file_system_tools import list_files as list_files_raw

    # 使用优化的路径解析
    resolver = get_path_resolver()
    resolved_path = resolver.resolve_workspace_path(path, workspace)

    # 调用原始工具
    return list_files_raw.func(resolved_path)


@tool_middleware(
    tool_name="optimized_glob_search",
    cache_policy=CachePolicy.TIME_BASED,
    cache_ttl=300,
)
def optimized_glob_search(
    pattern: str, path: Optional[str] = None, workspace: Optional[str] = None
) -> str:
    """
    优化的glob搜索工具

    Args:
        pattern: 搜索模式
        path: 搜索路径
        workspace: 工作区路径
    """
    from .file_system_tools import glob_search as glob_search_raw

    # 使用优化的路径解析
    resolver = get_path_resolver()
    if path:
        resolved_path = resolver.resolve_workspace_path(path, workspace)
    else:
        resolved_path = workspace

    # 调用原始工具
    return glob_search_raw.func(pattern, resolved_path)


@tool_middleware(
    tool_name="optimized_grep_search",
    cache_policy=CachePolicy.TIME_BASED,
    cache_ttl=300,
)
def optimized_grep_search(
    pattern: str,
    path: Optional[str] = None,
    include: Optional[str] = None,
    workspace: Optional[str] = None,
) -> str:
    """
    优化的grep搜索工具

    Args:
        pattern: 搜索模式
        path: 搜索路径
        include: 文件过滤
        workspace: 工作区路径
    """
    from .file_system_tools import grep_search as grep_search_raw

    # 使用优化的路径解析
    resolver = get_path_resolver()
    if path:
        resolved_path = resolver.resolve_workspace_path(path, workspace)
    else:
        resolved_path = workspace

    # 调用原始工具
    return grep_search_raw.func(pattern, resolved_path, include)


@tool_middleware(
    tool_name="optimized_edit_file", cache_policy=CachePolicy.NO_CACHE  # 编辑操作不缓存
)
def optimized_edit_file(
    file_path: str, old_string: str, new_string: str, workspace: Optional[str] = None
) -> str:
    """
    优化的文件编辑工具

    Args:
        file_path: 文件路径
        old_string: 旧字符串
        new_string: 新字符串
        workspace: 工作区路径
    """
    from .file_edit_tools import edit_file as edit_file_raw

    # 使用优化的路径解析
    resolver = get_path_resolver()
    resolved_path = resolver.resolve_workspace_path(file_path, workspace)

    # 调用原始工具
    result = edit_file_raw.func(resolved_path, old_string, new_string)

    # 清理相关缓存
    middleware = get_tool_middleware()
    middleware.cache.clear("optimized_view_file")

    return result


@tool_middleware(
    tool_name="optimized_bash_command",
    cache_policy=CachePolicy.NO_CACHE,  # 命令执行不缓存
)
def optimized_bash_command(
    command: str,
    timeout: Optional[int] = None,
    workspace: Optional[str] = None,
    run_in_background: bool = False,
) -> str:
    """
    优化的bash命令工具

    Args:
        command: shell命令
        timeout: 超时时间
        workspace: 工作区路径
        run_in_background: 是否后台运行
    """
    from .bash_tool import bash_command as bash_command_raw

    # 注册进程到资源管理器
    resource_manager = get_resource_manager()

    working_directory = workspace if workspace else None
    result = bash_command_raw.func(
        command, timeout, working_directory, run_in_background
    )

    # 如果是后台进程，注册到资源管理器
    if run_in_background and "PID:" in result:
        try:
            import re

            pid_match = re.search(r"PID: (\d+)", result)
            if pid_match:
                pid = pid_match.group(1)
                process_id = f"bash_process_{pid}"
                resource_manager.register_process(
                    process_id,
                    {
                        "pid": pid,
                        "command": command,
                        "working_directory": working_directory,
                        "start_time": time.time(),
                    },
                )
        except Exception as e:
            logger.warning(f"注册后台进程失败: {e}")

    return result


def create_optimized_workspace_tools(workspace: Optional[str] = None) -> List[callable]:
    """
    创建优化的工作区工具集

    Args:
        workspace: 工作区路径

    Returns:
        优化的工具列表
    """
    import functools

    # 为每个工具绑定workspace参数
    def bind_workspace(func, ws):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, workspace=ws, **kwargs)

        return wrapper

    tools = [
        bind_workspace(optimized_view_file, workspace),
        bind_workspace(optimized_list_files, workspace),
        bind_workspace(optimized_glob_search, workspace),
        bind_workspace(optimized_grep_search, workspace),
        bind_workspace(optimized_edit_file, workspace),
        bind_workspace(optimized_bash_command, workspace),
    ]

    return tools


def get_optimization_stats() -> Dict[str, Any]:
    """获取优化统计信息"""
    middleware = get_tool_middleware()
    path_resolver = get_path_resolver()
    resource_manager = get_resource_manager()

    return {
        "middleware_metrics": middleware.get_metrics(),
        "path_cache_stats": path_resolver.get_cache_stats(),
        "active_processes": resource_manager.get_active_processes(),
        "cache_config": {
            "policy": middleware.cache_config.policy.value,
            "ttl": middleware.cache_config.ttl,
            "max_size": middleware.cache_config.max_size,
        },
    }


def cleanup_all_optimized_resources():
    """清理所有优化资源"""
    try:
        # 清理中间件
        middleware = get_tool_middleware()
        middleware.cleanup()

        # 清理路径缓存
        path_resolver = get_path_resolver()
        path_resolver.clear_cache()

        # 清理资源管理器
        resource_manager = get_resource_manager()
        resource_manager.cleanup_all_resources()

        logger.info("所有优化资源已清理")
    except Exception as e:
        logger.error(f"清理优化资源失败: {e}")


# 导出优化工具
__all__ = [
    "optimized_view_file",
    "optimized_list_files",
    "optimized_glob_search",
    "optimized_grep_search",
    "optimized_edit_file",
    "optimized_bash_command",
    "create_optimized_workspace_tools",
    "get_optimization_stats",
    "cleanup_all_optimized_resources",
    "PathResolver",
    "OptimizedResourceManager",
]
