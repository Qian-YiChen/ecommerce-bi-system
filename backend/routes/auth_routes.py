"""
认证相关 API 路由
----------------
POST /api/auth/login     — 登录，返回 JWT Token
POST /api/auth/register  — 注册新用户（需 admin 权限）
GET  /api/auth/me        — 获取当前用户信息
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
            "token": "eyJhbG...",
            "user": {
                "user_id": 1,
                "username": "admin",
                "role": "admin"
            },
            "message": "登录成功"
        }

    失败响应:
        { "success": false, "token": null, "message": "用户名或密码错误" }
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"success": False, "token": None, "message": "请提供 JSON 请求体"}), 400

    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return jsonify({"success": False, "token": None, "message": "用户名和密码不能为空"}), 400

    # ── TODO: 替换为苏文韬的 get_user_by_username ──
    from database.db_service import get_user_by_username
    success, token, message = login(username, password, get_user_by_username)

    if not success:
        return jsonify({"success": False, "token": None, "message": message}), 401

    from auth.auth_service import decode_access_token
    payload = decode_access_token(token)

    return jsonify({
        "success": True,
        "token": token,
        "user": {
            "user_id": int(payload["sub"]),
            "username": payload["username"],
            "role": payload["role"],
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
        { "success": true, "message": "用户创建成功（ID: 2）" }
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"success": False, "message": "请提供 JSON 请求体"}), 400

    # ── TODO: 替换为苏文韬的函数 ──
    from database.db_service import check_user_exists, insert_user
    success, message = register(
        username=data.get("username", "").strip(),
        password=data.get("password", ""),
        role=data.get("role", "").strip(),
        check_exists_fn=check_user_exists,
        insert_user_fn=insert_user,
    )

    status_code = 201 if success else 400
    return jsonify({"success": success, "message": message}), status_code


@auth_bp.route("/me", methods=["GET"])
@jwt_required
def current_user():
    """
    获取当前登录用户信息

    响应:
        {
            "user_id": 1,
            "username": "admin",
            "role": "admin"
        }
    """
    return jsonify(g.current_user), 200
