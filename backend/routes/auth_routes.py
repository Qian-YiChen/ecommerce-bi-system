"""
认证相关 API 路由
----------------
POST /api/auth/login     — 登录，返回 JWT Token
POST /api/auth/register  — 注册新用户（需 admin 权限）
GET  /api/auth/me        — 获取当前用户信息

所有响应遵循统一格式（参见 docs/函数参数需求文档.md §4.1）：
  成功: {"success": true, "data": {...}, "message": "操作成功"}
  失败: {"success": false, "data": null, "error": "错误描述", "code": "ERROR_CODE"}
"""

from flask import Blueprint, request, jsonify, g
from middleware.jwt_middleware import jwt_required, role_required
from auth.auth_service import login, register

# ── 占位：苏文韬的数据库函数 ──────────────────────────────────
# 这两个函数将在苏文韬完成 db_service.py 后替换为实际导入
# from database.db_service import get_user_by_username, check_user_exists, insert_user
# 详见 docs/函数参数需求文档.md §2
# ──────────────────────────────────────────────────────────────

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.route("/login", methods=["POST"])
def login_route():
    """
    用户登录

    请求体:
        {
            "username": "string",
            "password": "string"
        }

    成功响应:
        {
            "success": true,
            "data": {
                "token": "eyJhbG...",
                "user": {
                    "user_id": 1,
                    "username": "admin",
                    "role": "admin"
                }
            },
            "message": "登录成功"
        }

    失败响应:
        {
            "success": false,
            "data": null,
            "error": "用户名或密码错误",
            "code": "AUTH_FAILED"
        }
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({
            "success": False, "data": None,
            "error": "请提供 JSON 请求体", "code": "BAD_REQUEST"
        }), 400

    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return jsonify({
            "success": False, "data": None,
            "error": "用户名和密码不能为空", "code": "VALIDATION_ERROR"
        }), 400

    # ── TODO: 替换为苏文韬的 get_user_by_username ──
    from database.db_service import get_user_by_username
    success, token, message = login(username, password, get_user_by_username)

    if not success:
        return jsonify({
            "success": False, "data": None,
            "error": message, "code": "AUTH_FAILED"
        }), 401

    from auth.auth_service import decode_access_token
    payload = decode_access_token(token)

    return jsonify({
        "success": True,
        "data": {
            "token": token,
            "user": {
                "user_id": int(payload["sub"]),
                "username": payload["username"],
                "role": payload["role"],
            },
        },
        "message": message,
    }), 200


@auth_bp.route("/register", methods=["POST"])
@jwt_required
@role_required("admin")
def register_route():
    """
    注册新用户（仅管理员）

    请求体:
        {
            "username": "string",   # 必填，≥3字符
            "password": "string",   # 必填，≥6字符
            "role": "string"        # 必填，admin/analyst/manager/viewer
        }

    成功响应:
        {
            "success": true,
            "data": null,
            "message": "用户创建成功（ID: 2）"
        }

    失败响应:
        {
            "success": false,
            "data": null,
            "error": "用户名已存在",
            "code": "REGISTER_FAILED"
        }
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({
            "success": False, "data": None,
            "error": "请提供 JSON 请求体", "code": "BAD_REQUEST"
        }), 400

    # ── TODO: 替换为苏文韬的函数 ──
    from database.db_service import check_user_exists, insert_user
    success, message = register(
        username=data.get("username", "").strip(),
        password=data.get("password", ""),
        role=data.get("role", "").strip(),
        check_exists_fn=check_user_exists,
        insert_user_fn=insert_user,
    )

    if not success:
        return jsonify({
            "success": False, "data": None,
            "error": message, "code": "REGISTER_FAILED"
        }), 400

    return jsonify({
        "success": True, "data": None, "message": message
    }), 201


@auth_bp.route("/me", methods=["GET"])
@jwt_required
def current_user():
    """
    获取当前登录用户信息

    成功响应:
        {
            "success": true,
            "data": {
                "user_id": 1,
                "username": "admin",
                "role": "admin"
            },
            "message": "ok"
        }
    """
    return jsonify({
        "success": True, "data": g.current_user, "message": "ok"
    }), 200
