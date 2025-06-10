# SPDX-License-Identifier: MIT

"""
Context压缩器实现
"""

from .base import BaseContext


class ContextCompressor:
    """Context压缩器"""

    def __init__(self, max_content_length: int = 1000):
        self.max_content_length = max_content_length

    async def compress(self, context: BaseContext) -> BaseContext:
        """压缩context"""
        if context.is_compressed:
            return context

        # 简单压缩：截断内容
        content_str = str(context.content)
        if len(content_str) > self.max_content_length:
            compressed_content = content_str[: self.max_content_length] + "..."
            context.content = compressed_content
            context.is_compressed = True

        return context
