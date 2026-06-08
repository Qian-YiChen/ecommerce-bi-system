"""
认证服务
-------
JWT Token 签发与验证、密码哈希、用户登录/注册逻辑。
依赖苏文韬的数据库连接模块（见 函数参数需求文档.md）。
"""

import time
import bcrypt
import jwt
from typing import Optional, Tuple

from config import get_config
from models.user import User

config = get_config()


# ═══════════════════════════════════════════════════════════════
# 密码哈希
# ═══════════════════════════════════════════════════════════════

def hash_password(plain_password: str) -> str:
    """将明文密码哈希为 bcrypt 字符串"""
    return bcrypt.hashpw(
        plain_password.encode("utf-8"),
        bcrypt.gensalt(rounds=config.BCRYPT_ROUNDS),
    ).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    """验证明文密码是否匹配哈希"""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        password_hash.encode("utf-8"),
    )


# ═══════════════════════════════════════════════════════════════
# JWT Token
# ═══════════════════════════════════════════════════════════════

def create_access_token(user: User) -> str:
    """为用户签发 JWT access token"""
    now = int(time.time())
    payload = {
        "sub": str(user.user_id),
        "username": user.username,
        "role": user.role,
        "iat": now,
        "exp": now + config.JWT_ACCESS_TOKEN_EXPIRES,
    }
    return jwt.encode(payload, config.JWT_SECRET_KEY, algorithm="HS256")


def decode_access_token(token: str) -> Optional[dict]:
    """验证并解析 JWT token，返回 payload；验证失败返回 None"""
    try:
        payload = jwt.decode(token, config.JWT_SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        return None  # Token 过期
    except jwt.InvalidTokenError:
        return None  # Token 无效


# ═══════════════════════════════════════════════════════════════
# 用户认证业务逻辑
# ═══════════════════════════════════════════════════════════════

# ── 注意 ──────────────────────────────────────────────────────
# 以下 login / register 函数中的数据库操作使用了占位函数
#   get_user_by_username(username) -> Optional[User]
#   insert_user(user: User) -> int (返回 user_id)
# 这两个函数由苏文韬在 backend/database/db_service.py 中实现。
# 具体接口约定见 docs/函数参数需求文档.md §2。
# ──────────────────────────────────────────────────────────────

def login(username: str, password: str, get_user_fn) -> Tuple[bool, Optional[str], str]:
    """
    用户登录

    参数:
        username: 用户名
        password: 明文密码
        get_user_fn: 函数 (str) -> Optional[User]，由苏文韬提供，根据用户名查询用户

    返回:
        (success, token, message)
        - success=True 时 token 为 JWT 字符串
        - success=False 时 token 为 None，message 为错误提示
    """
    user = get_user_fn(username)
    if user is None:
        return False, None, "用户名或密码错误"

    if not user.is_active():
        return False, None, "账号已被禁用，请联系管理员"

    if not verify_password(password, user.password_hash):
        return False, None, "用户名或密码错误"

    token = create_access_token(user)
    return True, token, "登录成功"


def register(
    username: str,
    password: str,
    role: str,
    check_exists_fn,
    insert_user_fn,
) -> Tuple[bool, str]:
    """
    用户注册（仅管理员可调用）

    参数:
        username: 用户名
        password: 明文密码
        role: 角色（admin / analyst / manager / viewer）
        check_exists_fn: 函数 (str) -> bool，由苏文韬提供
        insert_user_fn: 函数 (User) -> int，由苏文韬提供

    返回:
        (success, message)
    """
    if not username or len(username) < 3:
        return False, "用户名至少需要 3 个字符"

    if not password or len(password) < 6:
        return False, "密码至少需要 6 个字符"

    if role not in User.VALID_ROLES:
        return False, f"无效的角色：{role}，可选值：{User.VALID_ROLES}"

    if check_exists_fn(username):
        return False, "用户名已存在"

    password_hash = hash_password(password)
    user = User(username=username, password_hash=password_hash, role=role)
    user_id = insert_user_fn(user)

    return True, f"用户创建成功（ID: {user_id}）"
