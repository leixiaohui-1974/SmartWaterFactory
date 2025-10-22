#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""API密钥管理模块。

提供API密钥的生成、验证和管理功能，支持SaaS化部署。
"""

import secrets
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class APIKey:
    """API密钥数据类。"""
    key_id: str
    key_hash: str  # 存储哈希值，不存储原始密钥
    user_id: str
    name: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    last_used: Optional[datetime] = None
    is_active: bool = True
    permissions: List[str] = field(default_factory=list)
    rate_limit: int = 60  # 每分钟请求数
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """检查密钥是否过期。"""
        if not self.expires_at:
            return False
        return datetime.now() > self.expires_at

    def is_valid(self) -> bool:
        """检查密钥是否有效。"""
        return self.is_active and not self.is_expired()

    def to_dict(self, include_hash: bool = False) -> Dict[str, Any]:
        """转换为字典。"""
        data = {
            "key_id": self.key_id,
            "user_id": self.user_id,
            "name": self.name,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "is_active": self.is_active,
            "permissions": self.permissions,
            "rate_limit": self.rate_limit,
            "metadata": self.metadata
        }
        if include_hash:
            data["key_hash"] = self.key_hash
        return data


class APIKeyManager:
    """API密钥管理器。

    管理API密钥的生成、验证、撤销等操作。
    """

    def __init__(self):
        """初始化API密钥管理器。"""
        self._keys: Dict[str, APIKey] = {}  # key_id -> APIKey
        self._hash_to_id: Dict[str, str] = {}  # key_hash -> key_id
        self._user_keys: Dict[str, List[str]] = {}  # user_id -> [key_ids]

    @staticmethod
    def generate_key() -> str:
        """生成新的API密钥。

        格式: swf_<32字符随机字符串>

        Returns:
            API密钥字符串
        """
        random_part = secrets.token_urlsafe(24)[:32]
        return f"swf_{random_part}"

    @staticmethod
    def hash_key(api_key: str) -> str:
        """计算API密钥的哈希值。

        Args:
            api_key: API密钥

        Returns:
            SHA256哈希值
        """
        return hashlib.sha256(api_key.encode()).hexdigest()

    def create_key(
        self,
        user_id: str,
        name: str,
        expires_in_days: Optional[int] = None,
        permissions: Optional[List[str]] = None,
        rate_limit: int = 60,
        metadata: Optional[Dict[str, Any]] = None
    ) -> tuple[str, APIKey]:
        """创建新的API密钥。

        Args:
            user_id: 用户ID
            name: 密钥名称
            expires_in_days: 过期天数（None表示永不过期）
            permissions: 权限列表
            rate_limit: 速率限制（请求/分钟）
            metadata: 元数据

        Returns:
            (原始密钥, APIKey对象)
        """
        # 生成密钥
        raw_key = self.generate_key()
        key_hash = self.hash_key(raw_key)
        key_id = f"key_{secrets.token_hex(8)}"

        # 计算过期时间
        expires_at = None
        if expires_in_days:
            expires_at = datetime.now() + timedelta(days=expires_in_days)

        # 创建APIKey对象
        api_key = APIKey(
            key_id=key_id,
            key_hash=key_hash,
            user_id=user_id,
            name=name,
            created_at=datetime.now(),
            expires_at=expires_at,
            permissions=permissions or [],
            rate_limit=rate_limit,
            metadata=metadata or {}
        )

        # 保存密钥
        self._keys[key_id] = api_key
        self._hash_to_id[key_hash] = key_id

        # 更新用户索引
        if user_id not in self._user_keys:
            self._user_keys[user_id] = []
        self._user_keys[user_id].append(key_id)

        logger.info(f"Created API key {key_id} for user {user_id}")

        return raw_key, api_key

    def verify_key(self, api_key: str) -> Optional[APIKey]:
        """验证API密钥。

        Args:
            api_key: API密钥字符串

        Returns:
            如果有效则返回APIKey对象，否则返回None
        """
        # 计算哈希
        key_hash = self.hash_key(api_key)

        # 查找密钥
        key_id = self._hash_to_id.get(key_hash)
        if not key_id:
            return None

        api_key_obj = self._keys.get(key_id)
        if not api_key_obj:
            return None

        # 检查有效性
        if not api_key_obj.is_valid():
            return None

        # 更新最后使用时间
        api_key_obj.last_used = datetime.now()

        return api_key_obj

    def revoke_key(self, key_id: str) -> bool:
        """撤销API密钥。

        Args:
            key_id: 密钥ID

        Returns:
            是否成功撤销
        """
        if key_id not in self._keys:
            return False

        api_key = self._keys[key_id]
        api_key.is_active = False

        logger.info(f"Revoked API key {key_id}")
        return True

    def delete_key(self, key_id: str) -> bool:
        """删除API密钥。

        Args:
            key_id: 密钥ID

        Returns:
            是否成功删除
        """
        if key_id not in self._keys:
            return False

        api_key = self._keys[key_id]

        # 从索引中移除
        if api_key.key_hash in self._hash_to_id:
            del self._hash_to_id[api_key.key_hash]

        if api_key.user_id in self._user_keys:
            if key_id in self._user_keys[api_key.user_id]:
                self._user_keys[api_key.user_id].remove(key_id)
            if not self._user_keys[api_key.user_id]:
                del self._user_keys[api_key.user_id]

        # 删除密钥
        del self._keys[key_id]

        logger.info(f"Deleted API key {key_id}")
        return True

    def get_key(self, key_id: str) -> Optional[APIKey]:
        """获取API密钥信息。

        Args:
            key_id: 密钥ID

        Returns:
            APIKey对象或None
        """
        return self._keys.get(key_id)

    def list_user_keys(self, user_id: str, include_inactive: bool = False) -> List[APIKey]:
        """列出用户的所有API密钥。

        Args:
            user_id: 用户ID
            include_inactive: 是否包含未激活的密钥

        Returns:
            API密钥列表
        """
        key_ids = self._user_keys.get(user_id, [])
        keys = [self._keys[kid] for kid in key_ids if kid in self._keys]

        if not include_inactive:
            keys = [k for k in keys if k.is_valid()]

        return keys

    def cleanup_expired(self) -> int:
        """清理过期的密钥。

        Returns:
            清理的密钥数量
        """
        expired_keys = [
            key_id for key_id, api_key in self._keys.items()
            if api_key.is_expired()
        ]

        for key_id in expired_keys:
            self.delete_key(key_id)

        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired API keys")

        return len(expired_keys)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息。

        Returns:
            统计信息字典
        """
        total_keys = len(self._keys)
        active_keys = sum(1 for k in self._keys.values() if k.is_active)
        expired_keys = sum(1 for k in self._keys.values() if k.is_expired())

        return {
            "total_keys": total_keys,
            "active_keys": active_keys,
            "expired_keys": expired_keys,
            "total_users": len(self._user_keys)
        }


# 全局API密钥管理器实例
_global_manager = APIKeyManager()


def get_api_key_manager() -> APIKeyManager:
    """获取全局API密钥管理器。"""
    return _global_manager
