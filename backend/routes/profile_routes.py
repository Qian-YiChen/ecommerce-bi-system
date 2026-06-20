"""
用户画像 API 路由（P1）
-----------------------
GET /api/profile/users — 获取全量用户画像（调用薛淞 compute_user_profiles）

作者: 严辰乐
日期: 2026-06-20
"""

from flask import Blueprint, jsonify
from middleware.jwt_middleware import jwt_required

profile_bp = Blueprint("profile", __name__, url_prefix="/api/profile")


@profile_bp.route("/users", methods=["GET"])
@jwt_required
def get_user_profiles():
    """
    获取用户画像列表（从 user_profile 表读取）。

    ML 管道已通过 compute_user_profiles() 预计算画像并写入 user_profile 表，
    此路由直接从数据库读取，不重复计算。

    返回:
        {
            "success": true,
            "data": [
                {
                    "customer_id": 1,
                    "customer_name": "张***",
                    "value_level": "高价值",
                    "avg_order_price": 280.00,
                    "purchase_frequency": 3.2,
                    "preferred_category": "女装,美妆",
                    "promo_sensitivity": "高",
                    "last_purchase_date": "2026-06-05"
                },
                ...
            ],
            "message": "ok"
        }
    """
    try:
        from database.db_service import get_db_connection
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT up.*, c.customer_name, c.gender, c.age_group, c.region
                FROM user_profile up
                JOIN customer c ON up.customer_id = c.customer_id
                ORDER BY
                    FIELD(up.value_level, '高价值', '中价值', '低价值'),
                    up.avg_order_price DESC
            """)
            rows = cursor.fetchall()
        conn.close()

        profiles = []
        for r in rows:
            d = dict(r)
            for k, v in d.items():
                if hasattr(v, 'isoformat'):
                    d[k] = v.isoformat()
            profiles.append(d)

        return jsonify({
            "success": True,
            "data": profiles,
            "message": "ok"
        }), 200
    except ImportError as e:
        return jsonify({
            "success": False, "data": None,
            "error": f"模块导入失败: {e}", "code": "IMPORT_ERROR"
        }), 500
    except Exception as e:
        return jsonify({
            "success": False, "data": None,
            "error": f"查询画像失败: {e}", "code": "PROFILE_ERROR"
        }), 500
