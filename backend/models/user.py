"""
用户模型
-------
对应数据库 user 表，提供用户 CRUD 操作。
"""

from datetime import datetime
from typing import Optional


class User:
    """
    用户实体类

    对应数据库字段：
        user_id    INT PRIMARY KEY AUTO_INCREMENT
        username   VARCHAR(50)  NOT NULL UNIQUE
        password   VARCHAR(255) NOT NULL  -- bcrypt 哈希
        role       VARCHAR(20)  NOT NULL  -- admin / analyst / manager / viewer
        status     TINYINT      NOT NULL  -- 1=活跃 0=禁用
        created_at DATETIME     NOT NULL
    """

    VALID_ROLES = ("admin", "analyst", "manager", "viewer")

    def __init__(
        self,
        username: str,
        password_hash: str,
        role: str = "viewer",
        status: int = 1,
        user_id: Optional[int] = None,
        created_at: Optional[datetime] = None,
    ):
        self.user_id = user_id
        self.username = username
        self.password_hash = password_hash
        self.role = role
        self.status = status
        self.created_at = created_at or datetime.utcnow()

    def to_dict(self, include_password: bool = False) -> dict:
        """转为字典（默认不返回密码哈希）"""
        data = {
            "user_id": self.user_id,
            "username": self.username,
            "role": self.role,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_password:
            data["password_hash"] = self.password_hash
        return data

    def is_active(self) -> bool:
        return self.status == 1

    def has_role(self, *roles: str) -> bool:
        return self.role in roles
