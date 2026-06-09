"""
数据查询 API 路由（UC-01）
------------------------
GET /api/data/sales  — 多维度销售数据查询

所有响应遵循统一格式（参见 docs/函数参数需求文档.md §4.1）：
  成功: {"success": true, "data": {...}, "message": "操作成功"}
  失败: {"success": false, "data": null, "error": "错误描述", "code": "ERROR_CODE"}

作者: 苏文韬
日期: 2026-06-09
"""

from flask import Blueprint, request, jsonify
from middleware.jwt_middleware import jwt_required
from database.db_service import query_sales

data_bp = Blueprint("data", __name__, url_prefix="/api/data")


@data_bp.route("/sales", methods=["GET"])
@jwt_required
def query_sales_route():
    """
    多维度销售数据查询（UC-01）

    Query 参数:
        start_date  (必填) — "2025-01-01"
        end_date    (必填) — "2025-12-31"
        region      (可选) — None=全国, "广东", ...
        category_id (可选) — None=全品类, 1, 2, ...
        channel     (可选) — None=全渠道, "PC", "Mobile", "Miniprogram"
        group_by    (可选) — "day"（默认）| "week" | "month"

    成功响应:
        {
            "success": true,
            "data": {
                "summary": {
                    "total_sales": 1234567.89,
                    "total_orders": 5678,
                    "avg_order_value": 217.45,
                    "change_rate": 0.123
                },
                "series": [
                    {"date": "2025-01-01", "sales": 12345.67, "orders": 56},
                    ...
                ],
                "by_category": [
                    {"category_name": "服装", "sales": 500000, "percentage": 0.40},
                    ...
                ],
                "by_region": [
                    {"region": "广东", "sales": 300000, "percentage": 0.24},
                    ...
                ]
            },
            "message": "查询成功"
        }

    失败响应:
        {
            "success": false,
            "data": null,
            "error": "缺少必填参数 start_date",
            "code": "VALIDATION_ERROR"
        }
    """
    # ── 参数提取与校验 ──
    start_date = request.args.get("start_date", "").strip()
    end_date = request.args.get("end_date", "").strip()

    if not start_date:
        return jsonify({
            "success": False, "data": None,
            "error": "缺少必填参数 start_date", "code": "VALIDATION_ERROR"
        }), 400

    if not end_date:
        return jsonify({
            "success": False, "data": None,
            "error": "缺少必填参数 end_date", "code": "VALIDATION_ERROR"
        }), 400

    region = request.args.get("region", None)
    if region is not None:
        region = region.strip() or None

    category_id = request.args.get("category_id", None)
    if category_id is not None:
        try:
            category_id = int(category_id)
        except ValueError:
            return jsonify({
                "success": False, "data": None,
                "error": f"category_id 必须为整数，收到: {request.args.get('category_id')}",
                "code": "VALIDATION_ERROR"
            }), 400

    channel = request.args.get("channel", None)
    if channel is not None:
        channel = channel.strip() or None

    group_by = request.args.get("group_by", "day").strip()
    valid_group_by = ("day", "week", "month")
    if group_by not in valid_group_by:
        return jsonify({
            "success": False, "data": None,
            "error": f"group_by 参数无效: {group_by}，可选值：{valid_group_by}",
            "code": "VALIDATION_ERROR"
        }), 400

    # ── 调用苏文韬的 query_sales ──
    try:
        data = query_sales(
            start_date=start_date,
            end_date=end_date,
            region=region,
            category_id=category_id,
            channel=channel,
            group_by=group_by,
        )
    except ValueError as e:
        return jsonify({
            "success": False, "data": None,
            "error": str(e), "code": "VALIDATION_ERROR"
        }), 400
    except RuntimeError as e:
        return jsonify({
            "success": False, "data": None,
            "error": str(e), "code": "DATABASE_ERROR"
        }), 500

    return jsonify({
        "success": True,
        "data": data,
        "message": "查询成功"
    }), 200
