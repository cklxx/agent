# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT

"""
工具调用中间件层 - 提供统一的性能监控、错误处理、缓存和资源管理
"""

import asyncio
import time
import logging
import functools
import weakref
from typing import Any, Dict, Optional, Callable, Union, TypeVar, Generic
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor
import threading

logger = logging.getLogger(__name__)

# 类型定义
T = TypeVar("T")
ToolFunc = TypeVar("ToolFunc", bound=Callable)


class ToolResult(Generic[T]):
    """工具调用结果包装器"""

    def __init__(
        self,
        success: bool,
        data: Optional[T] = None,
        error: Optional[str] = None,
        execution_time: float = 0.0,
        from_cache: bool = False,
    ):
        self.success = success
        self.data = data
        self.error = error
        self.execution_time = execution_time
        self.from_cache = from_cache

    def __str__(self) -> str:
        if self.success:
            cache_info = " (from cache)" if self.from_cache else ""
            return f"{self.data}{cache_info}"
        else:
            return f"Error: {self.error}"


class ToolError(Exception):
    """工具调用错误基类"""

    def __init__(
        self,
        message: str,
        tool_name: str = "",
        original_error: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.tool_name = tool_name
        self.original_error = original_error


class ToolSecurityError(ToolError):
    """工具安全相关错误"""

    pass


class ToolTimeoutError(ToolError):
    """工具超时错误"""

    pass


class ToolResourceError(ToolError):
    """工具资源相关错误"""

    pass


@dataclass
class ToolMetrics:
    """工具调用指标"""

    tool_name: str
    call_count: int = 0
    total_time: float = 0.0
    error_count: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    last_called: Optional[float] = None

    @property
    def average_time(self) -> float:
        return self.total_time / self.call_count if self.call_count > 0 else 0.0

    @property
    def cache_hit_rate(self) -> float:
        total_cache_ops = self.cache_hits + self.cache_misses
        return self.cache_hits / total_cache_ops if total_cache_ops > 0 else 0.0


class CachePolicy(Enum):
    """缓存策略"""

    NO_CACHE = "no_cache"
    TIME_BASED = "time_based"  # 基于时间过期
    LRU = "lru"  # 最近最少使用
    INTELLIGENT = "intelligent"  # 智能缓存（基于调用频率和结果大小）


@dataclass
class CacheConfig:
    """缓存配置"""

    policy: CachePolicy = CachePolicy.TIME_BASED
    ttl: int = 300  # 秒
    max_size: int = 1000
    enable_compression: bool = True


class SmartCache:
    """智能缓存实现"""

    def __init__(self, config: CacheConfig):
        self.config = config
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._access_times: Dict[str, float] = {}
        self._access_counts: Dict[str, int] = {}
        self._lock = threading.RLock()

    def _generate_key(self, tool_name: str, args: tuple, kwargs: dict) -> str:
        """生成缓存键"""
        import hashlib

        key_data = f"{tool_name}:{args}:{sorted(kwargs.items())}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def _is_expired(self, cache_entry: Dict[str, Any]) -> bool:
        """检查缓存是否过期"""
        if self.config.policy == CachePolicy.NO_CACHE:
            return True

        if self.config.policy == CachePolicy.TIME_BASED:
            return time.time() - cache_entry["timestamp"] > self.config.ttl

        return False

    def _evict_if_needed(self):
        """根据策略清理缓存"""
        while len(self._cache) >= self.config.max_size:
            if self.config.policy == CachePolicy.LRU:
                # 移除最久未访问的条目
                if self._access_times:
                    oldest_key = min(
                        self._access_times.keys(), key=self._access_times.get
                    )
                    self._remove_entry(oldest_key)
                else:
                    break
            elif self.config.policy == CachePolicy.INTELLIGENT:
                # 智能清理：优先移除访问频率低且较大的条目
                entries = []
                for key, entry in self._cache.items():
                    size = len(str(entry.get("result", "")))
                    frequency = self._access_counts.get(key, 0)
                    score = frequency / (size + 1)  # 频率/大小比
                    entries.append((key, score))

                # 移除得分最低的条目
                if entries:
                    worst_key = min(entries, key=lambda x: x[1])[0]
                    self._remove_entry(worst_key)
                else:
                    break
            else:
                break

    def _remove_entry(self, key: str):
        """移除缓存条目"""
        self._cache.pop(key, None)
        self._access_times.pop(key, None)
        self._access_counts.pop(key, None)
        self._access_times.pop(key, None)
        self._access_counts.pop(key, None)

    def get(self, tool_name: str, args: tuple, kwargs: dict) -> Optional[Any]:
        """获取缓存结果"""
        if self.config.policy == CachePolicy.NO_CACHE:
            return None

        key = self._generate_key(tool_name, args, kwargs)

        with self._lock:
            if key not in self._cache:
                return None

            entry = self._cache[key]
            if self._is_expired(entry):
                self._remove_entry(key)
                return None

            # 更新访问信息
            self._access_times[key] = time.time()
            self._access_counts[key] = self._access_counts.get(key, 0) + 1

            return entry["result"]

    def set(self, tool_name: str, args: tuple, kwargs: dict, result: Any):
        """设置缓存结果"""
        if self.config.policy == CachePolicy.NO_CACHE:
            return

        key = self._generate_key(tool_name, args, kwargs)

        with self._lock:
            # 如果是新键且已达上限，先清理
            if key not in self._cache and len(self._cache) >= self.config.max_size:
                self._evict_if_needed()

            self._cache[key] = {
                "result": result,
                "timestamp": time.time(),
                "tool_name": tool_name,
            }
            self._access_times[key] = time.time()
            self._access_counts[key] = 1

    def clear(self, tool_name: Optional[str] = None):
        """清理缓存"""
        with self._lock:
            if tool_name is None:
                self._cache.clear()
                self._access_times.clear()
                self._access_counts.clear()
            else:
                keys_to_remove = [
                    key
                    for key, entry in self._cache.items()
                    if entry.get("tool_name") == tool_name
                ]
                for key in keys_to_remove:
                    self._remove_entry(key)


class ResourceManager:
    """资源管理器"""

    def __init__(self):
        self._resources: weakref.WeakSet = weakref.WeakSet()
        self._cleanup_callbacks: Dict[str, Callable] = {}
        self._lock = threading.RLock()

    def register_resource(
        self, resource: Any, cleanup_callback: Optional[Callable] = None
    ):
        """注册需要管理的资源"""
        with self._lock:
            self._resources.add(resource)
            if cleanup_callback:
                self._cleanup_callbacks[id(resource)] = cleanup_callback

    def cleanup_all(self):
        """清理所有资源"""
        with self._lock:
            for resource in list(self._resources):
                try:
                    cleanup_callback = self._cleanup_callbacks.get(id(resource))
                    if cleanup_callback:
                        cleanup_callback()
                    elif hasattr(resource, "close"):
                        resource.close()
                    elif hasattr(resource, "cleanup"):
                        resource.cleanup()
                except Exception as e:
                    logger.warning(f"清理资源时出错: {e}")

            self._resources.clear()
            self._cleanup_callbacks.clear()


class ToolMiddleware:
    """工具调用中间件"""

    def __init__(
        self,
        cache_config: Optional[CacheConfig] = None,
        enable_metrics: bool = True,
        max_workers: int = 4,
    ):
        self.cache_config = cache_config or CacheConfig()
        self.enable_metrics = enable_metrics

        # 初始化组件
        self.cache = SmartCache(self.cache_config)
        self.resource_manager = ResourceManager()
        self.metrics: Dict[str, ToolMetrics] = {}
        self._metrics_lock = threading.RLock()

        # 异步执行器
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.resource_manager.register_resource(self.executor, self.executor.shutdown)

    def _update_metrics(
        self, tool_name: str, execution_time: float, success: bool, from_cache: bool
    ):
        """更新工具调用指标"""
        if not self.enable_metrics:
            return

        with self._metrics_lock:
            if tool_name not in self.metrics:
                self.metrics[tool_name] = ToolMetrics(tool_name=tool_name)

            metric = self.metrics[tool_name]
            metric.call_count += 1
            metric.total_time += execution_time
            metric.last_called = time.time()

            if not success:
                metric.error_count += 1

            if from_cache:
                metric.cache_hits += 1
            else:
                metric.cache_misses += 1

    def get_metrics(
        self, tool_name: Optional[str] = None
    ) -> Union[ToolMetrics, Dict[str, ToolMetrics]]:
        """获取工具调用指标"""
        with self._metrics_lock:
            if tool_name:
                return self.metrics.get(tool_name, ToolMetrics(tool_name=tool_name))
            return self.metrics.copy()

    def clear_metrics(self, tool_name: Optional[str] = None):
        """清理指标"""
        with self._metrics_lock:
            if tool_name:
                self.metrics.pop(tool_name, None)
            else:
                self.metrics.clear()

    async def execute_async_tool(
        self, tool_func: Callable, tool_name: str, *args, **kwargs
    ) -> ToolResult:
        """执行异步工具"""
        start_time = time.time()

        try:
            # 检查缓存
            cached_result = self.cache.get(tool_name, args, kwargs)
            if cached_result is not None:
                execution_time = time.time() - start_time
                self._update_metrics(tool_name, execution_time, True, True)
                return ToolResult(
                    True, cached_result, execution_time=execution_time, from_cache=True
                )

            # 执行工具
            if asyncio.iscoroutinefunction(tool_func):
                result = await tool_func(*args, **kwargs)
            else:
                # 在线程池中执行同步函数
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    self.executor, tool_func, *args, **kwargs
                )

            execution_time = time.time() - start_time

            # 缓存结果
            self.cache.set(tool_name, args, kwargs, result)

            # 更新指标
            self._update_metrics(tool_name, execution_time, True, False)

            return ToolResult(True, result, execution_time=execution_time)

        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"{tool_name} failed: {str(e)}"

            # 更新指标
            self._update_metrics(tool_name, execution_time, False, False)

            # 记录错误
            logger.error(f"Tool execution failed: {error_msg}", exc_info=True)

            return ToolResult(False, error=error_msg, execution_time=execution_time)

    def execute_sync_tool(
        self, tool_func: Callable, tool_name: str, *args, **kwargs
    ) -> ToolResult:
        """执行同步工具（包装为异步结果）"""
        # 对于同步工具，我们创建一个简单的同步版本
        start_time = time.time()

        try:
            # 检查缓存
            cached_result = self.cache.get(tool_name, args, kwargs)
            if cached_result is not None:
                execution_time = time.time() - start_time
                self._update_metrics(tool_name, execution_time, True, True)
                return ToolResult(
                    True, cached_result, execution_time=execution_time, from_cache=True
                )

            # 执行工具
            result = tool_func(*args, **kwargs)
            execution_time = time.time() - start_time

            # 缓存结果
            self.cache.set(tool_name, args, kwargs, result)

            # 更新指标
            self._update_metrics(tool_name, execution_time, True, False)

            return ToolResult(True, result, execution_time=execution_time)

        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"{tool_name} failed: {str(e)}"

            # 更新指标
            self._update_metrics(tool_name, execution_time, False, False)

            # 记录错误
            logger.error(f"Tool execution failed: {error_msg}", exc_info=True)

            return ToolResult(False, error=error_msg, execution_time=execution_time)

    def wrap_tool(
        self, tool_func: ToolFunc, tool_name: Optional[str] = None
    ) -> ToolFunc:
        """包装工具函数以添加中间件功能"""
        actual_tool_name = tool_name or getattr(tool_func, "__name__", "unknown_tool")

        if asyncio.iscoroutinefunction(tool_func):

            @functools.wraps(tool_func)
            async def async_wrapper(*args, **kwargs):
                result = await self.execute_async_tool(
                    tool_func, actual_tool_name, *args, **kwargs
                )
                if result.success:
                    return result.data
                else:
                    raise ToolError(result.error, actual_tool_name)

            return async_wrapper
        else:

            @functools.wraps(tool_func)
            def sync_wrapper(*args, **kwargs):
                result = self.execute_sync_tool(
                    tool_func, actual_tool_name, *args, **kwargs
                )
                if result.success:
                    return result.data
                else:
                    raise ToolError(result.error, actual_tool_name)

            return sync_wrapper

    def cleanup(self):
        """清理中间件资源"""
        self.resource_manager.cleanup_all()
        self.cache.clear()
        self.clear_metrics()


# 全局中间件实例
_global_middleware: Optional[ToolMiddleware] = None


def get_tool_middleware(
    cache_config: Optional[CacheConfig] = None,
    enable_metrics: bool = True,
    max_workers: int = 4,
) -> ToolMiddleware:
    """获取全局工具中间件实例"""
    global _global_middleware

    if _global_middleware is None:
        _global_middleware = ToolMiddleware(
            cache_config=cache_config,
            enable_metrics=enable_metrics,
            max_workers=max_workers,
        )

    return _global_middleware


# 装饰器
def tool_middleware(
    tool_name: Optional[str] = None,
    cache_policy: CachePolicy = CachePolicy.TIME_BASED,
    cache_ttl: int = 300,
):
    """工具中间件装饰器"""

    def decorator(func: ToolFunc) -> ToolFunc:
        middleware = get_tool_middleware(
            cache_config=CacheConfig(policy=cache_policy, ttl=cache_ttl)
        )
        return middleware.wrap_tool(func, tool_name)

    return decorator
