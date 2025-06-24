# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT

"""
优化的异步工具操作模式 - 统一异步/同步工具调用
"""

import asyncio
import logging
import functools
from typing import Any, Callable, Optional, Union, Dict, List, Coroutine
from concurrent.futures import ThreadPoolExecutor, Future
import threading
import weakref

from .middleware import get_tool_middleware, ToolResult, ToolError

logger = logging.getLogger(__name__)


class AsyncToolManager:
    """异步工具管理器 - 统一管理异步和同步工具的执行"""

    def __init__(self, max_workers: int = 8):
        self.max_workers = max_workers
        self._executor: Optional[ThreadPoolExecutor] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._executor_lock = threading.Lock()
        self._shutdown = False

        # 活跃任务追踪
        self._active_tasks: weakref.WeakSet = weakref.WeakSet()
        self._task_lock = threading.Lock()

    @property
    def executor(self) -> ThreadPoolExecutor:
        """获取线程池执行器（懒加载）"""
        if self._shutdown:
            raise RuntimeError("AsyncToolManager has been shutdown")

        if self._executor is None or self._executor._shutdown:
            with self._executor_lock:
                if self._executor is None or self._executor._shutdown:
                    self._executor = ThreadPoolExecutor(
                        max_workers=self.max_workers, thread_name_prefix="async_tool_"
                    )
        return self._executor

    def _get_or_create_event_loop(self) -> asyncio.AbstractEventLoop:
        """获取或创建事件循环"""
        try:
            loop = asyncio.get_running_loop()
            return loop
        except RuntimeError:
            # 没有运行中的事件循环，创建新的
            if self._loop is None or self._loop.is_closed():
                self._loop = asyncio.new_event_loop()
            return self._loop

    async def execute_tool_async(
        self, tool_func: Callable, tool_name: str, *args, **kwargs
    ) -> Any:
        """异步执行工具（无论原始工具是同步还是异步）"""
        if self._shutdown:
            raise RuntimeError("AsyncToolManager has been shutdown")

        middleware = get_tool_middleware()

        try:
            if asyncio.iscoroutinefunction(tool_func):
                # 原生异步工具
                result = await middleware.execute_async_tool(
                    tool_func, tool_name, *args, **kwargs
                )
            else:
                # 同步工具转异步
                loop = asyncio.get_running_loop()
                result = await loop.run_in_executor(
                    self.executor,
                    lambda: middleware.execute_sync_tool(
                        tool_func, tool_name, *args, **kwargs
                    ),
                )

            if result.success:
                return result.data
            else:
                raise ToolError(result.error, tool_name)

        except Exception as e:
            logger.error(f"异步工具执行失败 {tool_name}: {e}")
            raise

    def execute_tool_sync(
        self, tool_func: Callable, tool_name: str, *args, **kwargs
    ) -> Any:
        """同步执行工具（处理异步工具的同步调用）"""
        middleware = get_tool_middleware()

        if asyncio.iscoroutinefunction(tool_func):
            # 异步工具的同步调用
            try:
                loop = asyncio.get_running_loop()
                # 如果已经在事件循环中，不能直接运行异步函数
                if loop.is_running():
                    # 使用线程池在新线程中运行事件循环
                    future = self.executor.submit(
                        self._run_async_in_thread, tool_func, tool_name, args, kwargs
                    )
                    return future.result()
                else:
                    # 直接运行异步函数
                    return loop.run_until_complete(
                        middleware.execute_async_tool(
                            tool_func, tool_name, *args, **kwargs
                        )
                    ).data
            except RuntimeError:
                # 没有事件循环，创建新的
                result = asyncio.run(
                    middleware.execute_async_tool(tool_func, tool_name, *args, **kwargs)
                )
                if result.success:
                    return result.data
                else:
                    raise ToolError(result.error, tool_name)
        else:
            # 同步工具的同步调用
            result = middleware.execute_sync_tool(tool_func, tool_name, *args, **kwargs)
            if result.success:
                return result.data
            else:
                raise ToolError(result.error, tool_name)

    def _run_async_in_thread(
        self, tool_func: Callable, tool_name: str, args: tuple, kwargs: dict
    ) -> Any:
        """在新线程中运行异步工具"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            middleware = get_tool_middleware()
            result = loop.run_until_complete(
                middleware.execute_async_tool(tool_func, tool_name, *args, **kwargs)
            )
            if result.success:
                return result.data
            else:
                raise ToolError(result.error, tool_name)
        finally:
            loop.close()

    async def execute_batch_async(
        self, tool_calls: List[Dict[str, Any]], max_concurrent: int = 5
    ) -> List[Any]:
        """批量异步执行工具"""
        semaphore = asyncio.Semaphore(max_concurrent)

        async def execute_single(call_info: Dict[str, Any]) -> Any:
            async with semaphore:
                tool_func = call_info["func"]
                tool_name = call_info.get(
                    "name", getattr(tool_func, "__name__", "unknown")
                )
                args = call_info.get("args", ())
                kwargs = call_info.get("kwargs", {})

                try:
                    return await self.execute_tool_async(
                        tool_func, tool_name, *args, **kwargs
                    )
                except Exception as e:
                    logger.error(f"批量执行工具 {tool_name} 失败: {e}")
                    return ToolError(str(e), tool_name)

        tasks = [execute_single(call) for call in tool_calls]

        with self._task_lock:
            for task in tasks:
                self._active_tasks.add(task)

        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return results
        finally:
            # 清理任务引用
            with self._task_lock:
                for task in tasks:
                    self._active_tasks.discard(task)

    def execute_batch_sync(
        self, tool_calls: List[Dict[str, Any]], max_concurrent: int = 5
    ) -> List[Any]:
        """批量同步执行工具"""
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                # 在运行的事件循环中，使用线程池
                future = self.executor.submit(
                    self._run_batch_in_thread, tool_calls, max_concurrent
                )
                return future.result()
            else:
                return loop.run_until_complete(
                    self.execute_batch_async(tool_calls, max_concurrent)
                )
        except RuntimeError:
            # 没有事件循环
            return asyncio.run(self.execute_batch_async(tool_calls, max_concurrent))

    def _run_batch_in_thread(
        self, tool_calls: List[Dict[str, Any]], max_concurrent: int = 5
    ) -> List[Any]:
        """在新线程中运行批量工具调用"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                self.execute_batch_async(tool_calls, max_concurrent)
            )
        finally:
            loop.close()

    async def cancel_all_tasks(self):
        """取消所有活跃任务"""
        with self._task_lock:
            tasks_to_cancel = list(self._active_tasks)

        for task in tasks_to_cancel:
            if hasattr(task, "cancel"):
                task.cancel()

        if tasks_to_cancel:
            await asyncio.gather(*tasks_to_cancel, return_exceptions=True)

    def shutdown(self):
        """关闭管理器"""
        self._shutdown = True

        if self._executor:
            self._executor.shutdown(wait=True)
            self._executor = None

        # 如果有自己的事件循环，关闭它
        if self._loop and not self._loop.is_closed():
            if self._loop.is_running():
                self._loop.call_soon_threadsafe(self._loop.stop)
            self._loop.close()
            self._loop = None


# 全局异步工具管理器
_global_async_manager: Optional[AsyncToolManager] = None
_manager_lock = threading.Lock()


def get_async_tool_manager(max_workers: int = 8) -> AsyncToolManager:
    """获取全局异步工具管理器"""
    global _global_async_manager

    if _global_async_manager is None or _global_async_manager._shutdown:
        with _manager_lock:
            if _global_async_manager is None or _global_async_manager._shutdown:
                _global_async_manager = AsyncToolManager(max_workers=max_workers)

    return _global_async_manager


def async_tool_wrapper(tool_name: Optional[str] = None):
    """异步工具包装器装饰器"""

    def decorator(func: Callable) -> Callable:
        actual_name = tool_name or getattr(func, "__name__", "unknown_tool")
        manager = get_async_tool_manager()

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await manager.execute_tool_async(func, actual_name, *args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            return manager.execute_tool_sync(func, actual_name, *args, **kwargs)

        # 添加两个版本的方法
        async_wrapper.sync = sync_wrapper
        sync_wrapper.async_version = async_wrapper

        # 默认返回异步版本
        return async_wrapper

    return decorator


def sync_tool_wrapper(tool_name: Optional[str] = None):
    """同步工具包装器装饰器"""

    def decorator(func: Callable) -> Callable:
        actual_name = tool_name or getattr(func, "__name__", "unknown_tool")
        manager = get_async_tool_manager()

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            return manager.execute_tool_sync(func, actual_name, *args, **kwargs)

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await manager.execute_tool_async(func, actual_name, *args, **kwargs)

        # 添加两个版本的方法
        sync_wrapper.async_version = async_wrapper
        async_wrapper.sync = sync_wrapper

        # 默认返回同步版本
        return sync_wrapper

    return decorator


class ToolExecutor:
    """工具执行器 - 提供便捷的工具执行接口"""

    def __init__(self, manager: Optional[AsyncToolManager] = None):
        self.manager = manager or get_async_tool_manager()

    async def run_async(self, tool_func: Callable, *args, **kwargs) -> Any:
        """异步运行工具"""
        tool_name = getattr(tool_func, "__name__", "unknown_tool")
        return await self.manager.execute_tool_async(
            tool_func, tool_name, *args, **kwargs
        )

    def run_sync(self, tool_func: Callable, *args, **kwargs) -> Any:
        """同步运行工具"""
        tool_name = getattr(tool_func, "__name__", "unknown_tool")
        return self.manager.execute_tool_sync(tool_func, tool_name, *args, **kwargs)

    async def run_batch_async(
        self, tool_calls: List[Dict[str, Any]], max_concurrent: int = 5
    ) -> List[Any]:
        """批量异步运行工具"""
        return await self.manager.execute_batch_async(tool_calls, max_concurrent)

    def run_batch_sync(
        self, tool_calls: List[Dict[str, Any]], max_concurrent: int = 5
    ) -> List[Any]:
        """批量同步运行工具"""
        return self.manager.execute_batch_sync(tool_calls, max_concurrent)


# 便捷函数
async def run_tool_async(tool_func: Callable, *args, **kwargs) -> Any:
    """异步运行工具（便捷函数）"""
    executor = ToolExecutor()
    return await executor.run_async(tool_func, *args, **kwargs)


def run_tool_sync(tool_func: Callable, *args, **kwargs) -> Any:
    """同步运行工具（便捷函数）"""
    executor = ToolExecutor()
    return executor.run_sync(tool_func, *args, **kwargs)


async def run_tools_batch_async(
    tool_calls: List[Dict[str, Any]], max_concurrent: int = 5
) -> List[Any]:
    """批量异步运行工具（便捷函数）"""
    executor = ToolExecutor()
    return await executor.run_batch_async(tool_calls, max_concurrent)


def run_tools_batch_sync(
    tool_calls: List[Dict[str, Any]], max_concurrent: int = 5
) -> List[Any]:
    """批量同步运行工具（便捷函数）"""
    executor = ToolExecutor()
    return executor.run_batch_sync(tool_calls, max_concurrent)
