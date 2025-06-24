# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT

import logging
import os
import time
import threading
from typing import Optional, Dict, Any
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class OptimizedJinaClient:
    """优化的Jina客户端，支持连接池、重试机制和缓存"""

    def __init__(
        self,
        pool_connections: int = 10,
        pool_maxsize: int = 20,
        max_retries: int = 3,
        cache_ttl: int = 300,
    ):
        self.cache_ttl = cache_ttl
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_lock = threading.RLock()

        # 创建优化的会话
        self.session = requests.Session()

        # 配置重试策略
        retry_strategy = Retry(
            total=max_retries,
            status_forcelist=[429, 500, 502, 503, 504],
            backoff_factor=1,
            allowed_methods=["POST"],
        )

        # 配置HTTP适配器
        adapter = HTTPAdapter(
            pool_connections=pool_connections,
            pool_maxsize=pool_maxsize,
            max_retries=retry_strategy,
        )

        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def _get_cache_key(self, url: str, return_format: str) -> str:
        """生成缓存键"""
        import hashlib

        key_data = f"{url}:{return_format}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def _is_cache_valid(self, cache_entry: Dict[str, Any]) -> bool:
        """检查缓存是否有效"""
        return time.time() - cache_entry["timestamp"] < self.cache_ttl

    def _get_from_cache(self, url: str, return_format: str) -> Optional[str]:
        """从缓存获取结果"""
        cache_key = self._get_cache_key(url, return_format)

        with self._cache_lock:
            if cache_key in self._cache:
                entry = self._cache[cache_key]
                if self._is_cache_valid(entry):
                    logger.debug(f"Cache hit for URL: {url}")
                    return entry["content"]
                else:
                    # 移除过期缓存
                    del self._cache[cache_key]

        return None

    def _set_cache(self, url: str, return_format: str, content: str):
        """设置缓存"""
        cache_key = self._get_cache_key(url, return_format)

        with self._cache_lock:
            # 限制缓存大小
            if len(self._cache) >= 100:
                # 移除最老的条目
                oldest_key = min(
                    self._cache.keys(), key=lambda k: self._cache[k]["timestamp"]
                )
                del self._cache[oldest_key]

            self._cache[cache_key] = {"content": content, "timestamp": time.time()}

    def crawl(self, url: str, return_format: str = "html") -> str:
        """
        爬取URL内容，支持缓存和连接池优化

        Args:
            url: 要爬取的URL
            return_format: 返回格式

        Returns:
            爬取的内容
        """
        # 检查缓存
        cached_content = self._get_from_cache(url, return_format)
        if cached_content:
            return cached_content

        # 准备请求头
        headers = {
            "Content-Type": "application/json",
            "X-Return-Format": return_format,
            "User-Agent": "OptimizedJinaClient/1.0",
        }

        if os.getenv("JINA_API_KEY"):
            headers["Authorization"] = f"Bearer {os.getenv('JINA_API_KEY')}"
        else:
            logger.warning(
                "Jina API key is not set. Provide your own key to access a higher rate limit. "
                "See https://jina.ai/reader for more information."
            )

        data = {"url": url}

        # 配置代理
        proxies = None
        if os.getenv("PYTEST_CURRENT_TEST"):
            proxies = {"http": None, "https": None}

        try:
            start_time = time.time()

            response = self.session.post(
                "https://r.jina.ai/",
                headers=headers,
                json=data,
                proxies=proxies,
                timeout=30,
            )
            response.raise_for_status()

            content = response.text
            request_time = time.time() - start_time

            logger.info(f"Successfully crawled {url} in {request_time:.2f}s")

            # 缓存结果
            self._set_cache(url, return_format, content)

            return content

        except requests.exceptions.ProxyError as e:
            logger.warning(f"Proxy error: {e}. Retrying without proxy...")

            # 重试不使用代理
            try:
                response = self.session.post(
                    "https://r.jina.ai/",
                    headers=headers,
                    json=data,
                    proxies={"http": None, "https": None},
                    timeout=30,
                )
                response.raise_for_status()

                content = response.text
                self._set_cache(url, return_format, content)
                return content

            except Exception as retry_error:
                logger.error(f"Retry failed: {retry_error}")
                raise

        except requests.exceptions.Timeout as e:
            logger.error(f"Request timeout for {url}: {e}")
            raise

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {url}: {e}")
            raise

    def clear_cache(self):
        """清理缓存"""
        with self._cache_lock:
            self._cache.clear()

    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self._cache_lock:
            return {
                "cache_size": len(self._cache),
                "cache_entries": list(self._cache.keys()),
            }

    def close(self):
        """关闭客户端"""
        if self.session:
            self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# 保持向后兼容性
class JinaClient:
    """保持向后兼容的Jina客户端"""

    def __init__(self):
        self._optimized_client = OptimizedJinaClient()

    def crawl(self, url: str, return_format: str = "html") -> str:
        return self._optimized_client.crawl(url, return_format)


# 全局优化客户端实例
_global_jina_client: Optional[OptimizedJinaClient] = None
_client_lock = threading.Lock()


def get_jina_client() -> OptimizedJinaClient:
    """获取全局优化的Jina客户端"""
    global _global_jina_client

    if _global_jina_client is None:
        with _client_lock:
            if _global_jina_client is None:
                _global_jina_client = OptimizedJinaClient()

    return _global_jina_client
