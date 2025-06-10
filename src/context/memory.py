# SPDX-License-Identifier: MIT

"""
Context记忆管理实现
"""

import asyncio
import json
import os
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import OrderedDict

from .base import BaseContext, ContextType, Priority, ContextStorage


class WorkingMemory:
    """工作记忆实现，基于内存的快速访问"""

    def __init__(self, limit: int = 50):
        """
        初始化工作记忆

        Args:
            limit: 最大容量
        """
        self.limit = limit
        self._contexts: OrderedDict[str, BaseContext] = OrderedDict()
        self._lock = asyncio.Lock()

    async def add(self, context: BaseContext) -> bool:
        """添加context到工作记忆"""
        async with self._lock:
            # 如果已存在，更新位置
            if context.id in self._contexts:
                del self._contexts[context.id]

            # 检查容量限制
            while len(self._contexts) >= self.limit:
                # 移除最旧的context
                oldest_id, _ = self._contexts.popitem(last=False)

            self._contexts[context.id] = context
            self._contexts.move_to_end(context.id)  # 移动到最新位置
            return True

    async def get(self, context_id: str) -> Optional[BaseContext]:
        """获取context"""
        async with self._lock:
            context = self._contexts.get(context_id)
            if context:
                # 更新访问时间并移动到最新位置
                context.update_access()
                self._contexts.move_to_end(context_id)
            return context

    async def remove(self, context_id: str) -> bool:
        """删除context"""
        async with self._lock:
            if context_id in self._contexts:
                del self._contexts[context_id]
                return True
            return False

    async def get_all(self) -> List[BaseContext]:
        """获取所有contexts"""
        async with self._lock:
            return list(self._contexts.values())

    async def search(self, query: str, limit: int = 10) -> List[BaseContext]:
        """简单的文本搜索"""
        async with self._lock:
            results = []
            query_lower = query.lower()

            for context in self._contexts.values():
                content_str = str(context.content).lower()
                if query_lower in content_str or any(
                    query_lower in tag.lower() for tag in context.tags
                ):
                    results.append(context)

            # 按相关性排序（简单实现）
            results.sort(key=lambda x: x.last_access, reverse=True)
            return results[:limit]

    def size(self) -> int:
        """获取当前大小"""
        return len(self._contexts)


class SQLiteStorage(ContextStorage):
    """基于SQLite的长期存储实现"""

    def __init__(self, db_path: str = "temp/contexts.db"):
        """
        初始化SQLite存储

        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """初始化数据库表"""
        # 确保数据库目录存在
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS contexts (
                    id TEXT PRIMARY KEY,
                    context_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT,
                    timestamp TEXT NOT NULL,
                    priority INTEGER NOT NULL,
                    tags TEXT,
                    parent_id TEXT,
                    related_ids TEXT,
                    is_active INTEGER NOT NULL,
                    is_compressed INTEGER NOT NULL,
                    access_count INTEGER NOT NULL,
                    last_access TEXT NOT NULL
                )
            """
            )

    async def save(self, context: BaseContext) -> bool:
        """保存context"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO contexts 
                    (id, context_type, content, metadata, timestamp, priority, tags, 
                     parent_id, related_ids, is_active, is_compressed, access_count, last_access)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        context.id,
                        context.context_type.value,
                        (
                            json.dumps(context.content)
                            if isinstance(context.content, dict)
                            else str(context.content)
                        ),
                        json.dumps(context.metadata),
                        context.timestamp.isoformat(),
                        context.priority.value,
                        json.dumps(context.tags),
                        context.parent_id,
                        json.dumps(context.related_ids),
                        1 if context.is_active else 0,
                        1 if context.is_compressed else 0,
                        context.access_count,
                        context.last_access.isoformat(),
                    ),
                )
            return True
        except Exception:
            return False

    async def load(self, context_id: str) -> Optional[BaseContext]:
        """加载context"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT * FROM contexts WHERE id = ?", (context_id,)
                )
                row = cursor.fetchone()
                if row:
                    return self._row_to_context(row)
            return None
        except Exception:
            return None

    async def delete(self, context_id: str) -> bool:
        """删除context"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "DELETE FROM contexts WHERE id = ?", (context_id,)
                )
                return cursor.rowcount > 0
        except Exception:
            return False

    async def search(
        self, query: str, context_type: Optional[ContextType] = None, limit: int = 10
    ) -> List[BaseContext]:
        """搜索contexts"""
        try:
            query_lower = query.lower()
            sql = "SELECT * FROM contexts WHERE (LOWER(content) LIKE ? OR LOWER(tags) LIKE ?)"
            params = [f"%{query_lower}%", f"%{query_lower}%"]

            if context_type:
                sql += " AND context_type = ?"
                params.append(context_type.value)

            sql += " ORDER BY last_access DESC LIMIT ?"
            params.append(limit)

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(sql, params)
                rows = cursor.fetchall()
                return [self._row_to_context(row) for row in rows]
        except Exception:
            return []

    async def list_by_type(
        self, context_type: ContextType, limit: int = 10
    ) -> List[BaseContext]:
        """按类型列出contexts"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT * FROM contexts 
                    WHERE context_type = ? 
                    ORDER BY last_access DESC 
                    LIMIT ?
                """,
                    (context_type.value, limit),
                )
                rows = cursor.fetchall()
                return [self._row_to_context(row) for row in rows]
        except Exception:
            return []

    def _row_to_context(self, row) -> BaseContext:
        """将数据库行转换为Context对象"""
        (
            id,
            context_type,
            content,
            metadata,
            timestamp,
            priority,
            tags,
            parent_id,
            related_ids,
            is_active,
            is_compressed,
            access_count,
            last_access,
        ) = row

        # 解析JSON字段
        try:
            parsed_content = json.loads(content)
        except:
            parsed_content = content

        return BaseContext(
            id=id,
            context_type=ContextType(context_type),
            content=parsed_content,
            metadata=json.loads(metadata) if metadata else {},
            timestamp=datetime.fromisoformat(timestamp),
            priority=Priority(priority),
            tags=json.loads(tags) if tags else [],
            parent_id=parent_id,
            related_ids=json.loads(related_ids) if related_ids else [],
            is_active=bool(is_active),
            is_compressed=bool(is_compressed),
            access_count=access_count,
            last_access=datetime.fromisoformat(last_access),
        )


class LongTermMemory:
    """长期记忆实现"""

    def __init__(self, storage: Optional[ContextStorage] = None):
        """
        初始化长期记忆

        Args:
            storage: 存储后端，默认使用SQLite
        """
        self.storage = storage or SQLiteStorage()

    async def save(self, context: BaseContext) -> bool:
        """保存context到长期记忆"""
        return await self.storage.save(context)

    async def load(self, context_id: str) -> Optional[BaseContext]:
        """从长期记忆加载context"""
        return await self.storage.load(context_id)

    async def delete(self, context_id: str) -> bool:
        """从长期记忆删除context"""
        return await self.storage.delete(context_id)
