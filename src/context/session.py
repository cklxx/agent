"""
会话管理模块
实现同一个会话使用同一个context，不同会话之间的上下文不互通
"""

import asyncio
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Optional, Set, Any
import uuid
import json
import os

from .manager import ContextManager
from .base import ContextType, Priority

logger = logging.getLogger(__name__)


class SessionManager:
    """会话管理器，负责管理不同会话之间的上下文隔离"""

    def __init__(self, db_path: str = "temp/sessions.db"):
        """
        初始化会话管理器

        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self.active_sessions: Dict[str, ContextManager] = {}
        self.session_metadata: Dict[str, Dict[str, Any]] = {}

        # 确保temp目录存在
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        # 初始化数据库
        self._init_database()

        # 清理过期会话的定时任务
        self._cleanup_interval = 3600  # 1小时清理一次
        self._max_session_age = 86400 * 7  # 会话最大存活时间：7天

        logger.info(f"SessionManager初始化完成，数据库路径: {db_path}")

    def _init_database(self):
        """初始化会话数据库"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 创建会话表
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_access TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT,
                    is_active BOOLEAN DEFAULT 1
                )
            """
            )

            # 创建会话上下文关联表
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS session_contexts (
                    session_id TEXT,
                    context_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions (session_id)
                )
            """
            )

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"初始化数据库失败: {e}")
            raise

    async def create_session(self, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        创建新会话

        Args:
            metadata: 会话元数据

        Returns:
            会话ID
        """
        session_id = str(uuid.uuid4())

        # 创建专用的ContextManager
        context_manager = ContextManager()
        self.active_sessions[session_id] = context_manager

        # 保存会话元数据
        session_metadata = metadata or {}
        session_metadata.update(
            {
                "created_at": datetime.now().isoformat(),
                "last_access": datetime.now().isoformat(),
            }
        )
        self.session_metadata[session_id] = session_metadata

        # 保存到数据库
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO sessions (session_id, metadata)
                VALUES (?, ?)
            """,
                (session_id, json.dumps(session_metadata)),
            )

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"保存会话到数据库失败: {e}")
            # 清理内存中的会话
            self.active_sessions.pop(session_id, None)
            self.session_metadata.pop(session_id, None)
            raise

        logger.info(f"创建新会话: {session_id}")
        return session_id

    async def get_session_context_manager(
        self, session_id: str
    ) -> Optional[ContextManager]:
        """
        获取指定会话的ContextManager

        Args:
            session_id: 会话ID

        Returns:
            ContextManager实例，如果会话不存在则返回None
        """
        if session_id not in self.active_sessions:
            # 尝试从数据库恢复会话
            if await self._restore_session(session_id):
                logger.info(f"从数据库恢复会话: {session_id}")
            else:
                logger.warning(f"会话不存在: {session_id}")
                return None

        # 更新最后访问时间
        await self._update_session_access(session_id)

        return self.active_sessions[session_id]

    async def _restore_session(self, session_id: str) -> bool:
        """
        从数据库恢复会话

        Args:
            session_id: 会话ID

        Returns:
            是否成功恢复
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 查询会话信息
            cursor.execute(
                """
                SELECT metadata, is_active FROM sessions 
                WHERE session_id = ?
            """,
                (session_id,),
            )

            result = cursor.fetchone()
            if not result or not result[1]:  # 会话不存在或已非活跃
                conn.close()
                return False

            metadata_str, is_active = result
            metadata = json.loads(metadata_str) if metadata_str else {}

            # 创建ContextManager并恢复到内存
            context_manager = ContextManager()
            self.active_sessions[session_id] = context_manager
            self.session_metadata[session_id] = metadata

            conn.close()
            return True

        except Exception as e:
            logger.error(f"恢复会话失败: {e}")
            return False

    async def _update_session_access(self, session_id: str):
        """更新会话的最后访问时间"""
        try:
            # 更新内存中的元数据
            if session_id in self.session_metadata:
                self.session_metadata[session_id][
                    "last_access"
                ] = datetime.now().isoformat()

            # 更新数据库
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE sessions 
                SET last_access = CURRENT_TIMESTAMP 
                WHERE session_id = ?
            """,
                (session_id,),
            )

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"更新会话访问时间失败: {e}")

    async def end_session(self, session_id: str):
        """
        结束会话

        Args:
            session_id: 会话ID
        """
        try:
            # 从内存中移除
            self.active_sessions.pop(session_id, None)
            self.session_metadata.pop(session_id, None)

            # 在数据库中标记为非活跃
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE sessions 
                SET is_active = 0 
                WHERE session_id = ?
            """,
                (session_id,),
            )

            conn.commit()
            conn.close()

            logger.info(f"会话已结束: {session_id}")

        except Exception as e:
            logger.error(f"结束会话失败: {e}")

    async def list_active_sessions(self) -> Dict[str, Dict[str, Any]]:
        """
        列出所有活跃会话

        Returns:
            会话ID到元数据的映射
        """
        return self.session_metadata.copy()

    async def cleanup_expired_sessions(self):
        """清理过期的会话"""
        try:
            cutoff_time = datetime.now() - timedelta(seconds=self._max_session_age)
            expired_sessions = []

            # 查找过期的会话
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT session_id FROM sessions 
                WHERE last_access < ? AND is_active = 1
            """,
                (cutoff_time.isoformat(),),
            )

            expired_sessions = [row[0] for row in cursor.fetchall()]

            # 标记为非活跃
            if expired_sessions:
                placeholders = ",".join(["?" for _ in expired_sessions])
                cursor.execute(
                    f"""
                    UPDATE sessions 
                    SET is_active = 0 
                    WHERE session_id IN ({placeholders})
                """,
                    expired_sessions,
                )

                conn.commit()

            conn.close()

            # 从内存中移除过期会话
            for session_id in expired_sessions:
                self.active_sessions.pop(session_id, None)
                self.session_metadata.pop(session_id, None)

            if expired_sessions:
                logger.info(f"清理了 {len(expired_sessions)} 个过期会话")

        except Exception as e:
            logger.error(f"清理过期会话失败: {e}")

    async def get_session_stats(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        获取会话统计信息

        Args:
            session_id: 会话ID

        Returns:
            统计信息字典
        """
        context_manager = await self.get_session_context_manager(session_id)
        if not context_manager:
            return None

        stats = context_manager.get_stats()
        session_metadata = self.session_metadata.get(session_id, {})

        return {
            "session_id": session_id,
            "created_at": session_metadata.get("created_at"),
            "last_access": session_metadata.get("last_access"),
            "context_stats": stats,
        }


# 全局会话管理器实例
_global_session_manager = None


def get_session_manager() -> SessionManager:
    """获取全局会话管理器实例"""
    global _global_session_manager
    if _global_session_manager is None:
        _global_session_manager = SessionManager()
    return _global_session_manager


async def create_session(metadata: Optional[Dict[str, Any]] = None) -> str:
    """便捷函数：创建新会话"""
    return await get_session_manager().create_session(metadata)


async def get_session_context(session_id: str) -> Optional[ContextManager]:
    """便捷函数：获取会话的上下文管理器"""
    return await get_session_manager().get_session_context_manager(session_id)


async def end_session(session_id: str):
    """便捷函数：结束会话"""
    await get_session_manager().end_session(session_id)
