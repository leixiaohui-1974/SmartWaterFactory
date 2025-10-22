#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MCP会话管理模块。

负责管理用户会话，支持多用户并发访问。
每个会话包含独立的仿真实例、数据存储和资源管理。
"""

import uuid
import time
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path
import threading

from ..models.schemas import SessionInfo
from ..config import get_config

logger = logging.getLogger(__name__)


@dataclass
class SimulationInstance:
    """仿真实例。"""
    simulator: Any = None
    status: str = "idle"  # idle, running, paused, completed, error
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    current_step: int = 0
    total_steps: int = 0
    results: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class UserSession:
    """用户会话。"""
    session_id: str
    user_id: str
    created_at: datetime
    last_active: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

    # 仿真实例
    simulations: Dict[str, SimulationInstance] = field(default_factory=dict)

    # 资源使用统计
    total_tool_calls: int = 0
    total_simulation_time: float = 0.0

    # 会话数据存储
    data: Dict[str, Any] = field(default_factory=dict)

    def to_info(self) -> SessionInfo:
        """转换为SessionInfo。"""
        return SessionInfo(
            session_id=self.session_id,
            user_id=self.user_id,
            created_at=self.created_at,
            last_active=self.last_active,
            metadata=self.metadata
        )

    def update_activity(self):
        """更新最后活动时间。"""
        self.last_active = datetime.now()

    def is_expired(self, timeout_minutes: int) -> bool:
        """检查会话是否过期。"""
        timeout = timedelta(minutes=timeout_minutes)
        return datetime.now() - self.last_active > timeout


class SessionManager:
    """会话管理器。

    管理所有用户会话，支持：
    - 会话创建和销毁
    - 会话过期自动清理
    - 并发控制
    - 资源隔离
    """

    def __init__(self):
        """初始化会话管理器。"""
        self._sessions: Dict[str, UserSession] = {}
        self._user_sessions: Dict[str, List[str]] = {}  # user_id -> session_ids
        self._lock = threading.RLock()
        self._cleanup_task: Optional[asyncio.Task] = None
        self.config = get_config()

        logger.info("SessionManager initialized")

    def create_session(
        self,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> UserSession:
        """创建新会话。

        Args:
            user_id: 用户ID
            metadata: 可选的元数据

        Returns:
            创建的会话对象

        Raises:
            RuntimeError: 如果超过最大并发会话数
        """
        with self._lock:
            # 检查并发会话限制
            if len(self._sessions) >= self.config.max_concurrent_sessions:
                raise RuntimeError(
                    f"Maximum concurrent sessions ({self.config.max_concurrent_sessions}) reached"
                )

            # 生成会话ID
            session_id = str(uuid.uuid4())

            # 创建会话
            now = datetime.now()
            session = UserSession(
                session_id=session_id,
                user_id=user_id,
                created_at=now,
                last_active=now,
                metadata=metadata or {}
            )

            # 保存会话
            self._sessions[session_id] = session

            # 添加到用户会话索引
            if user_id not in self._user_sessions:
                self._user_sessions[user_id] = []
            self._user_sessions[user_id].append(session_id)

            # 创建会话数据目录
            session_dir = Path(self.config.data_dir) / session_id
            session_dir.mkdir(parents=True, exist_ok=True)

            logger.info(f"Created session {session_id} for user {user_id}")

            return session

    def get_session(self, session_id: str) -> Optional[UserSession]:
        """获取会话。

        Args:
            session_id: 会话ID

        Returns:
            会话对象，如果不存在则返回None
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.update_activity()
            return session

    def delete_session(self, session_id: str) -> bool:
        """删除会话。

        Args:
            session_id: 会话ID

        Returns:
            是否成功删除
        """
        with self._lock:
            if session_id not in self._sessions:
                return False

            session = self._sessions[session_id]

            # 清理仿真实例
            for sim in session.simulations.values():
                if sim.simulator:
                    # 停止仿真（如果正在运行）
                    # TODO: 实现优雅停止
                    pass

            # 从索引中移除
            if session.user_id in self._user_sessions:
                self._user_sessions[session.user_id].remove(session_id)
                if not self._user_sessions[session.user_id]:
                    del self._user_sessions[session.user_id]

            # 删除会话
            del self._sessions[session_id]

            logger.info(f"Deleted session {session_id}")

            return True

    def list_sessions(
        self,
        user_id: Optional[str] = None
    ) -> List[SessionInfo]:
        """列出会话。

        Args:
            user_id: 可选的用户ID过滤

        Returns:
            会话信息列表
        """
        with self._lock:
            if user_id:
                session_ids = self._user_sessions.get(user_id, [])
                sessions = [self._sessions[sid] for sid in session_ids if sid in self._sessions]
            else:
                sessions = list(self._sessions.values())

            return [s.to_info() for s in sessions]

    def get_user_sessions(self, user_id: str) -> List[UserSession]:
        """获取用户的所有会话。

        Args:
            user_id: 用户ID

        Returns:
            会话列表
        """
        with self._lock:
            session_ids = self._user_sessions.get(user_id, [])
            return [self._sessions[sid] for sid in session_ids if sid in self._sessions]

    def count_sessions(self, user_id: Optional[str] = None) -> int:
        """统计会话数量。

        Args:
            user_id: 可选的用户ID

        Returns:
            会话数量
        """
        with self._lock:
            if user_id:
                return len(self._user_sessions.get(user_id, []))
            return len(self._sessions)

    def cleanup_expired_sessions(self) -> int:
        """清理过期会话。

        Returns:
            清理的会话数量
        """
        timeout = self.config.session_timeout_minutes
        expired_sessions = []

        with self._lock:
            for session_id, session in self._sessions.items():
                if session.is_expired(timeout):
                    expired_sessions.append(session_id)

        # 删除过期会话
        count = 0
        for session_id in expired_sessions:
            if self.delete_session(session_id):
                count += 1

        if count > 0:
            logger.info(f"Cleaned up {count} expired sessions")

        return count

    async def start_cleanup_task(self):
        """启动定期清理任务。"""
        if self._cleanup_task and not self._cleanup_task.done():
            logger.warning("Cleanup task already running")
            return

        async def cleanup_loop():
            while True:
                try:
                    await asyncio.sleep(60)  # 每分钟检查一次
                    self.cleanup_expired_sessions()
                except Exception as e:
                    logger.error(f"Error in cleanup task: {e}", exc_info=True)

        self._cleanup_task = asyncio.create_task(cleanup_loop())
        logger.info("Started session cleanup task")

    def stop_cleanup_task(self):
        """停止清理任务。"""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            logger.info("Stopped session cleanup task")

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息。

        Returns:
            统计信息字典
        """
        with self._lock:
            total_simulations = sum(
                len(session.simulations)
                for session in self._sessions.values()
            )

            active_simulations = sum(
                1 for session in self._sessions.values()
                for sim in session.simulations.values()
                if sim.status == "running"
            )

            return {
                "total_sessions": len(self._sessions),
                "total_users": len(self._user_sessions),
                "total_simulations": total_simulations,
                "active_simulations": active_simulations,
                "max_sessions": self.config.max_concurrent_sessions,
                "session_timeout_minutes": self.config.session_timeout_minutes
            }


# 全局会话管理器实例
_global_manager = SessionManager()


def get_session_manager() -> SessionManager:
    """获取全局会话管理器。"""
    return _global_manager
