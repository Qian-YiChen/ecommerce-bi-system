"""
用户管理 API 路由（P1）
-----------------------
GET   /api/admin/users              — 用户列表（分页+搜索）
POST  /api/admin/users              — 创建用户（admin）
PUT   /api/admin/users/<user_id>    — 更新用户信息（admin）
PUT   /api/admin/users/<user_id>/toggle-status — 切换启用/禁用（admin）

作者: 严辰乐
日期: 2026-06-20
"""

from flask import Blueprint, request, jsonify, g
from middleware.jwt_middleware import jwt_required, role_required
from database.db_service import get_db_connection
import pymysql

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


def _row_to_dict(row):
    if row is None:
        return None
    d = dict(row)
    for k, v in d.items():
        if hasattr(v, 'isoformat'):
            d[k] = v.isoformat()
    # 不返回密码哈希
    d.pop('password', None)
    return d


# ═══════════════════════════════════════════════════════════════
#  GET /api/admin/users — 用户列表
# ═══════════════════════════════════════════════════════════════
@admin_bp.route("/users", methods=["GET"])
@jwt_required
@role_required("admin")
def list_users():
    """
    获取系统用户列表（支持搜索和分页）。

    Query 参数:
        page:     页码，默认 1
        per_page: 每页条数，默认 20
        search:   搜索关键词（匹配 username）
        role:     按角色筛选
        status:   按状态筛选（1=活跃，0=禁用）

    返回:
        {success, data: {users: [...], pagination: {page, per_page, total, total_pages}}}
    """
    try:
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 20, type=int)
        search = request.args.get("search", "").strip()
        role_filter = request.args.get("role", "").strip()
        status_filter = request.args.get("status", type=int)

        page = max(1, page)
        per_page = max(1, min(100, per_page))

        conn = get_db_connection()

        where = []
        params = []
        if search:
            where.append("username LIKE %s")
            params.append(f"%{search}%")
        if role_filter:
            where.append("role = %s")
            params.append(role_filter)
        if status_filter is not None:
            where.append("status = %s")
            params.append(status_filter)

        where_sql = (" WHERE " + " AND ".join(where)) if where else ""

        # 总数
        with conn.cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) AS total FROM user{where_sql}", params)
            total = cursor.fetchone()["total"]

        # 当前页
        offset = (page - 1) * per_page
        with conn.cursor() as cursor:
            cursor.execute(
                f"SELECT user_id, username, role, status, created_at FROM user"
                f"{where_sql} ORDER BY user_id LIMIT %s OFFSET %s",
                params + [per_page, offset]
            )
            rows = cursor.fetchall()

        conn.close()

        users = [_row_to_dict(r) for r in rows]
        total_pages = max(1, (total + per_page - 1) // per_page)

        return jsonify({
            "success": True,
            "data": {
                "users": users,
                "pagination": {"page": page, "per_page": per_page,
                               "total": total, "total_pages": total_pages}
            },
            "message": "ok"
        }), 200
    except pymysql.MySQLError as e:
        return jsonify({
            "success": False, "data": None,
            "error": f"查询用户列表失败: {e}", "code": "DB_ERROR"
        }), 500


# ═══════════════════════════════════════════════════════════════
#  POST /api/admin/users — 创建用户
# ═══════════════════════════════════════════════════════════════
@admin_bp.route("/users", methods=["POST"])
@jwt_required
@role_required("admin")
def create_user():
    """
    创建新用户（管理员专用）。

    请求体:
        {username, password, role}
        role 可选: admin / analyst / manager / viewer

    返回:
        201: {success, data: {user_id, username, role}, message}
    """
    from auth.auth_service import hash_password
    from models.user import User

    data = request.get_json(silent=True)
    if not data:
        return jsonify({
            "success": False, "data": None,
            "error": "请提供 JSON 请求体", "code": "BAD_REQUEST"
        }), 400

    username = data.get("username", "").strip()
    password = data.get("password", "")
    role = data.get("role", "viewer").strip()

    if not username or len(username) < 3:
        return jsonify({
            "success": False, "data": None,
            "error": "用户名至少需要 3 个字符", "code": "VALIDATION_ERROR"
        }), 400
    if not password or len(password) < 6:
        return jsonify({
            "success": False, "data": None,
            "error": "密码至少需要 6 个字符", "code": "VALIDATION_ERROR"
        }), 400
    if role not in User.VALID_ROLES:
        return jsonify({
            "success": False, "data": None,
            "error": f"无效角色: {role}，可选: {User.VALID_ROLES}", "code": "VALIDATION_ERROR"
        }), 400

    try:
        conn = get_db_connection()
        # 检查重复
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1 FROM user WHERE username = %s", (username,))
            if cursor.fetchone():
                conn.close()
                return jsonify({
                    "success": False, "data": None,
                    "error": "用户名已存在", "code": "DUPLICATE"
                }), 409

        pw_hash = hash_password(password)
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO user (username, password, role, status, created_at) "
                "VALUES (%s, %s, %s, 1, NOW())",
                (username, pw_hash, role)
            )
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()

        return jsonify({
            "success": True,
            "data": {"user_id": new_id, "username": username, "role": role},
            "message": f"用户 {username} 创建成功"
        }), 201
    except pymysql.MySQLError as e:
        return jsonify({
            "success": False, "data": None,
            "error": f"创建用户失败: {e}", "code": "DB_ERROR"
        }), 500


# ═══════════════════════════════════════════════════════════════
#  PUT /api/admin/users/<user_id> — 更新用户
# ═══════════════════════════════════════════════════════════════
@admin_bp.route("/users/<int:user_id>", methods=["PUT"])
@jwt_required
@role_required("admin")
def update_user(user_id):
    """
    更新用户信息（管理员专用）。

    请求体（所有字段可选）:
        {username, password, role}

    返回:
        200: {success, data: null, message: "用户信息已更新"}
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({
            "success": False, "data": None,
            "error": "请提供 JSON 请求体", "code": "BAD_REQUEST"
        }), 400

    updates = {}
    if "username" in data:
        u = data["username"].strip()
        if len(u) < 3:
            return jsonify({
                "success": False, "data": None,
                "error": "用户名至少需要 3 个字符", "code": "VALIDATION_ERROR"
            }), 400
        updates["username"] = u
    if "password" in data:
        p = data["password"]
        if len(p) < 6:
            return jsonify({
                "success": False, "data": None,
                "error": "密码至少需要 6 个字符", "code": "VALIDATION_ERROR"
            }), 400
        from auth.auth_service import hash_password
        updates["password"] = hash_password(p)
    if "role" in data:
        from models.user import User
        r = data["role"].strip()
        if r not in User.VALID_ROLES:
            return jsonify({
                "success": False, "data": None,
                "error": f"无效角色: {r}", "code": "VALIDATION_ERROR"
            }), 400
        updates["role"] = r

    if not updates:
        return jsonify({
            "success": False, "data": None,
            "error": "未提供任何要更新的字段", "code": "VALIDATION_ERROR"
        }), 400

    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1 FROM user WHERE user_id = %s", (user_id,))
            if cursor.fetchone() is None:
                conn.close()
                return jsonify({
                    "success": False, "data": None,
                    "error": f"用户 {user_id} 不存在", "code": "NOT_FOUND"
                }), 404

        set_clause = ", ".join(f"{k} = %s" for k in updates)
        values = list(updates.values()) + [user_id]
        with conn.cursor() as cursor:
            cursor.execute(f"UPDATE user SET {set_clause} WHERE user_id = %s", values)
        conn.commit()
        conn.close()

        return jsonify({
            "success": True, "data": None,
            "message": "用户信息已更新"
        }), 200
    except pymysql.IntegrityError:
        return jsonify({
            "success": False, "data": None,
            "error": "用户名已存在", "code": "DUPLICATE"
        }), 409
    except pymysql.MySQLError as e:
        return jsonify({
            "success": False, "data": None,
            "error": f"更新用户失败: {e}", "code": "DB_ERROR"
        }), 500


# ═══════════════════════════════════════════════════════════════
#  PUT /api/admin/users/<user_id>/toggle-status — 切换状态
# ═══════════════════════════════════════════════════════════════
@admin_bp.route("/users/<int:user_id>/toggle-status", methods=["PUT"])
@jwt_required
@role_required("admin")
def toggle_user_status(user_id):
    """
    切换用户启用/禁用状态（管理员专用）。

    返回:
        200: {success, data: {user_id, new_status}, message}
    """
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT user_id, status FROM user WHERE user_id = %s", (user_id,)
            )
            row = cursor.fetchone()
            if row is None:
                conn.close()
                return jsonify({
                    "success": False, "data": None,
                    "error": f"用户 {user_id} 不存在", "code": "NOT_FOUND"
                }), 404

            new_status = 0 if row["status"] == 1 else 1
            cursor.execute(
                "UPDATE user SET status = %s WHERE user_id = %s",
                (new_status, user_id)
            )
        conn.commit()
        conn.close()

        return jsonify({
            "success": True,
            "data": {"user_id": user_id, "new_status": new_status},
            "message": "用户已启用" if new_status == 1 else "用户已禁用"
        }), 200
    except pymysql.MySQLError as e:
        return jsonify({
            "success": False, "data": None,
            "error": f"切换状态失败: {e}", "code": "DB_ERROR"
        }), 500
