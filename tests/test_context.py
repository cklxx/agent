#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Context模块测试
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, Mock
from src.context.base import (
    BaseContext,
    ContextType,
    Priority,
    ContextStorage,
    ContextProcessor,
)


class TestContextType:
    """ContextType枚举测试"""

    def test_context_type_values(self):
        """测试ContextType的各个值"""
        assert ContextType.CONVERSATION.value == "conversation"
        assert ContextType.TASK.value == "task"
        assert ContextType.KNOWLEDGE.value == "knowledge"
        assert ContextType.SYSTEM.value == "system"
        assert ContextType.CODE.value == "code"
        assert ContextType.FILE.value == "file"
        assert ContextType.EXECUTION.value == "execution"


class TestPriority:
    """Priority枚举测试"""

    def test_priority_values(self):
        """测试Priority的各个值"""
        assert Priority.LOW.value == 1
        assert Priority.MEDIUM.value == 2
        assert Priority.HIGH.value == 3
        assert Priority.CRITICAL.value == 4


class TestBaseContext:
    """BaseContext类测试"""

    def test_default_initialization(self):
        """测试默认初始化"""
        context = BaseContext()

        assert context.id is not None
        assert len(context.id) > 0
        assert context.context_type == ContextType.CONVERSATION
        assert context.content == ""
        assert context.metadata == {}
        assert isinstance(context.timestamp, datetime)
        assert context.priority == Priority.MEDIUM
        assert context.tags == []
        assert context.parent_id is None
        assert context.related_ids == []
        assert context.is_active is True
        assert context.is_compressed is False
        assert context.access_count == 0
        assert isinstance(context.last_access, datetime)

    def test_custom_initialization(self):
        """测试自定义初始化"""
        custom_time = datetime(2023, 1, 1, 12, 0, 0)
        context = BaseContext(
            context_type=ContextType.CODE,
            content="test content",
            metadata={"key": "value"},
            timestamp=custom_time,
            priority=Priority.HIGH,
            tags=["tag1", "tag2"],
            parent_id="parent123",
            related_ids=["rel1", "rel2"],
            is_active=False,
            is_compressed=True,
            access_count=5,
            last_access=custom_time,
        )

        assert context.context_type == ContextType.CODE
        assert context.content == "test content"
        assert context.metadata == {"key": "value"}
        assert context.timestamp == custom_time
        assert context.priority == Priority.HIGH
        assert context.tags == ["tag1", "tag2"]
        assert context.parent_id == "parent123"
        assert context.related_ids == ["rel1", "rel2"]
        assert context.is_active is False
        assert context.is_compressed is True
        assert context.access_count == 5
        assert context.last_access == custom_time

    def test_to_dict(self):
        """测试to_dict方法"""
        context = BaseContext(
            context_type=ContextType.TASK,
            content="test content",
            metadata={"key": "value"},
            priority=Priority.HIGH,
            tags=["tag1"],
            parent_id="parent123",
        )

        result = context.to_dict()

        assert isinstance(result, dict)
        assert result["context_type"] == "task"
        assert result["content"] == "test content"
        assert result["metadata"] == {"key": "value"}
        assert result["priority"] == 3
        assert result["tags"] == ["tag1"]
        assert result["parent_id"] == "parent123"
        assert "timestamp" in result
        assert "last_access" in result
        assert "id" in result

    def test_from_dict(self):
        """测试from_dict方法"""
        data = {
            "id": "test-id-123",
            "context_type": "code",
            "content": "test content",
            "metadata": {"key": "value"},
            "timestamp": "2023-01-01T12:00:00",
            "priority": 3,
            "tags": ["tag1", "tag2"],
            "parent_id": "parent123",
            "related_ids": ["rel1", "rel2"],
            "is_active": False,
            "is_compressed": True,
            "access_count": 10,
            "last_access": "2023-01-01T12:30:00",
        }

        context = BaseContext.from_dict(data)

        assert context.id == "test-id-123"
        assert context.context_type == ContextType.CODE
        assert context.content == "test content"
        assert context.metadata == {"key": "value"}
        assert context.priority == Priority.HIGH
        assert context.tags == ["tag1", "tag2"]
        assert context.parent_id == "parent123"
        assert context.related_ids == ["rel1", "rel2"]
        assert context.is_active is False
        assert context.is_compressed is True
        assert context.access_count == 10

    def test_from_dict_with_defaults(self):
        """测试from_dict方法使用默认值"""
        data = {}
        context = BaseContext.from_dict(data)

        assert context.id is not None
        assert context.context_type == ContextType.CONVERSATION
        assert context.content == ""
        assert context.metadata == {}
        assert context.priority == Priority.MEDIUM
        assert context.tags == []
        assert context.parent_id is None
        assert context.related_ids == []
        assert context.is_active is True
        assert context.is_compressed is False
        assert context.access_count == 0

    def test_update_access(self):
        """测试update_access方法"""
        context = BaseContext()
        initial_count = context.access_count
        initial_time = context.last_access

        # 等待一小段时间确保时间戳变化
        import time

        time.sleep(0.01)

        context.update_access()

        assert context.access_count == initial_count + 1
        assert context.last_access > initial_time

    def test_dict_content_support(self):
        """测试字典类型的content"""
        content_dict = {"type": "code", "language": "python", "lines": 100}
        context = BaseContext(content=content_dict)

        assert context.content == content_dict

        # 测试序列化和反序列化
        data = context.to_dict()
        restored_context = BaseContext.from_dict(data)
        assert restored_context.content == content_dict


class MockContextStorage(ContextStorage):
    """Mock ContextStorage for testing"""

    def __init__(self):
        self.storage = {}

    async def save(self, context: BaseContext) -> bool:
        self.storage[context.id] = context
        return True

    async def load(self, context_id: str) -> BaseContext:
        return self.storage.get(context_id)

    async def delete(self, context_id: str) -> bool:
        if context_id in self.storage:
            del self.storage[context_id]
            return True
        return False

    async def search(self, query: str, context_type=None, limit: int = 10):
        results = []
        for context in self.storage.values():
            if query.lower() in str(context.content).lower():
                if context_type is None or context.context_type == context_type:
                    results.append(context)
        return results[:limit]

    async def list_by_type(self, context_type: ContextType, limit: int = 10):
        results = [
            ctx for ctx in self.storage.values() if ctx.context_type == context_type
        ]
        return results[:limit]


class TestContextStorage:
    """ContextStorage测试"""

    @pytest.mark.asyncio
    async def test_mock_storage_save_and_load(self):
        """测试MockStorage的保存和加载功能"""
        storage = MockContextStorage()
        context = BaseContext(content="test content")

        # 测试保存
        result = await storage.save(context)
        assert result is True

        # 测试加载
        loaded_context = await storage.load(context.id)
        assert loaded_context is not None
        assert loaded_context.content == "test content"
        assert loaded_context.id == context.id

    @pytest.mark.asyncio
    async def test_mock_storage_delete(self):
        """测试MockStorage的删除功能"""
        storage = MockContextStorage()
        context = BaseContext(content="test content")

        # 保存然后删除
        await storage.save(context)
        result = await storage.delete(context.id)
        assert result is True

        # 确认已删除
        loaded_context = await storage.load(context.id)
        assert loaded_context is None

        # 删除不存在的ID
        result = await storage.delete("non-existent")
        assert result is False

    @pytest.mark.asyncio
    async def test_mock_storage_search(self):
        """测试MockStorage的搜索功能"""
        storage = MockContextStorage()

        context1 = BaseContext(content="python code example")
        context2 = BaseContext(content="javascript tutorial")
        context3 = BaseContext(content="python tutorial", context_type=ContextType.CODE)

        await storage.save(context1)
        await storage.save(context2)
        await storage.save(context3)

        # 搜索包含"python"的内容
        results = await storage.search("python")
        assert len(results) == 2

        # 按类型搜索
        results = await storage.search("python", context_type=ContextType.CODE)
        assert len(results) == 1
        assert results[0].id == context3.id

    @pytest.mark.asyncio
    async def test_mock_storage_list_by_type(self):
        """测试MockStorage的按类型列表功能"""
        storage = MockContextStorage()

        context1 = BaseContext(context_type=ContextType.CODE)
        context2 = BaseContext(context_type=ContextType.TASK)
        context3 = BaseContext(context_type=ContextType.CODE)

        await storage.save(context1)
        await storage.save(context2)
        await storage.save(context3)

        # 获取CODE类型的context
        code_contexts = await storage.list_by_type(ContextType.CODE)
        assert len(code_contexts) == 2

        # 获取TASK类型的context
        task_contexts = await storage.list_by_type(ContextType.TASK)
        assert len(task_contexts) == 1


class MockContextProcessor(ContextProcessor):
    """Mock ContextProcessor for testing"""

    def __init__(self, supported_types=None):
        self.supported_types = supported_types or [ContextType.CONVERSATION]
        self.processed_contexts = []

    async def process(self, context: BaseContext) -> BaseContext:
        # 简单的处理：在content前添加前缀
        processed_context = BaseContext(
            id=context.id,
            context_type=context.context_type,
            content=f"PROCESSED: {context.content}",
            metadata=context.metadata,
            timestamp=context.timestamp,
            priority=context.priority,
            tags=context.tags + ["processed"],
            parent_id=context.parent_id,
            related_ids=context.related_ids,
            is_active=context.is_active,
            is_compressed=context.is_compressed,
            access_count=context.access_count,
            last_access=context.last_access,
        )
        self.processed_contexts.append(processed_context)
        return processed_context

    def can_process(self, context: BaseContext) -> bool:
        return context.context_type in self.supported_types


class TestContextProcessor:
    """ContextProcessor测试"""

    @pytest.mark.asyncio
    async def test_mock_processor_can_process(self):
        """测试MockProcessor的can_process方法"""
        processor = MockContextProcessor([ContextType.CODE, ContextType.TASK])

        code_context = BaseContext(context_type=ContextType.CODE)
        task_context = BaseContext(context_type=ContextType.TASK)
        conv_context = BaseContext(context_type=ContextType.CONVERSATION)

        assert processor.can_process(code_context) is True
        assert processor.can_process(task_context) is True
        assert processor.can_process(conv_context) is False

    @pytest.mark.asyncio
    async def test_mock_processor_process(self):
        """测试MockProcessor的process方法"""
        processor = MockContextProcessor()
        context = BaseContext(content="original content", tags=["tag1"])

        processed = await processor.process(context)

        assert processed.content == "PROCESSED: original content"
        assert "processed" in processed.tags
        assert "tag1" in processed.tags
        assert processed.id == context.id
        assert len(processor.processed_contexts) == 1
