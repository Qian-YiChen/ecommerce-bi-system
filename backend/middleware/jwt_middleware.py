"""
JWT 认证中间件
-------------
Flask 请求拦截器：从 Authorization Header 中提取并验证 JWT Token，
验证通过后将用户信息注入 request.current_user。
"""

from functools import wraps
from flask import request, jsonify, g

from auth.auth_service import decode_access_token


def jwt_required(f):
    """
    JWT 认证装饰器

    用法:
        @app.route("/api/protected")
        @jwt_required
        def protected():
            user = g.current_user  # {"user_id": ..., "username": ..., "role": ...}
            ...

    Token 格式:
        Authorization: Bearer <jwt_token>
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "未提供认证令牌", "code": "TOKEN_MISSING"}), 401

        token = auth_header[7:]  # 去掉 "Bearer " 前缀
        payload = decode_access_token(token)

        if payload is None:
            return jsonify({"error": "认证令牌无效或已过期，请重新登录", "code": "TOKEN_INVALID"}), 401

        g.current_user = {
            "user_id": int(payload["sub"]),
            "username": payload["username"],
            "role": payload["role"],
        }
        return f(*args, **kwargs)

    return decorated


def role_required(*roles: str):
    """
    角色权限装饰器（需配合 @jwt_required 使用）

    用法:
        @app.route("/api/admin/users")
        @jwt_required
        @role_required("admin")
        def manage_users():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user = g.get("current_user")
            if user is None:
                return jsonify({"error": "未认证", "code": "UNAUTHORIZED"}), 401
            if user["role"] not in roles:
                return jsonify({"error": "权限不足", "code": "FORBIDDEN"}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator
