"""
数据源管理 API 路由（P1）
-------------------------
GET  /api/admin/datasource/status   — 数据库状态概览
GET  /api/admin/datasource/history  — 数据导入历史
POST /api/admin/datasource/upload   — 上传CSV/Excel（预留）

作者: 严辰乐
日期: 2026-06-20
"""

from flask import Blueprint, request, jsonify
from middleware.jwt_middleware import jwt_required, role_required
from database.db_service import get_db_connection
import pymysql

datasource_bp = Blueprint("datasource", __name__, url_prefix="/api/admin/datasource")


# ═══════════════════════════════════════════════════════════════
#  GET /api/admin/datasource/status — 数据库状态
# ═══════════════════════════════════════════════════════════════
@datasource_bp.route("/status", methods=["GET"])
@jwt_required
@role_required("admin")
def get_status():
    """
    获取数据库各表记录数及最后更新时间的状态概览。

    返回:
        {success, data: {tables: [{name, row_count, last_updated}], db_size_mb}}
    """
    try:
        conn = get_db_connection()
        table_names = [
            "user", "category", "product", "customer",
            "sales_record", "user_profile", "sales_forecast",
            "alert_rule", "alert_log", "campaign"
        ]

        tables = []
        with conn.cursor() as cursor:
            for t in table_names:
                cursor.execute(f"SELECT COUNT(*) AS cnt FROM `{t}`")
                row = cursor.fetchone()
                tables.append({
                    "name": t,
                    "row_count": row["cnt"],
                })

            # 最近销售记录时间
            cursor.execute("SELECT MAX(order_date) AS last_order FROM sales_record")
            last = cursor.fetchone()
            last_order = last["last_order"].isoformat() if last and last["last_order"] else None

            # 最近预测时间
            cursor.execute("SELECT MAX(created_at) AS last_fc FROM sales_forecast")
            fc = cursor.fetchone()
            last_forecast = fc["last_fc"].isoformat() if fc and fc["last_fc"] else None

            # 最近告警时间
            cursor.execute("SELECT MAX(trigger_time) AS last_alert FROM alert_log")
            la = cursor.fetchone()
            last_alert = la["last_alert"].isoformat() if la and la["last_alert"] else None

        conn.close()

        return jsonify({
            "success": True,
            "data": {
                "tables": tables,
                "last_order": last_order,
                "last_forecast": last_forecast,
                "last_alert": last_alert,
            },
            "message": "ok"
        }), 200
    except pymysql.MySQLError as e:
        return jsonify({
            "success": False, "data": None,
            "error": f"查询数据源状态失败: {e}", "code": "DB_ERROR"
        }), 500


# ═══════════════════════════════════════════════════════════════
#  GET /api/admin/datasource/history — 导入历史
# ═══════════════════════════════════════════════════════════════
@datasource_bp.route("/history", methods=["GET"])
@jwt_required
@role_required("admin")
def get_history():
    """
    获取数据导入历史记录（基于 sales_record 时间范围 + alert_log 操作记录）。

    返回:
        {success, data: {records: [{source, imported_at, record_count, status}]}}
    """
    try:
        conn = get_db_connection()
        records = []

        with conn.cursor() as cursor:
            # 销售数据覆盖范围
            cursor.execute(
                "SELECT MIN(order_date) AS first_order, MAX(order_date) AS last_order, "
                "COUNT(*) AS total FROM sales_record"
            )
            row = cursor.fetchone()
            if row and row["total"] > 0:
                records.append({
                    "source": "init.sql / seed_data.sql",
                    "imported_at": row["last_order"].isoformat() if hasattr(row["last_order"], 'isoformat') else str(row["last_order"]),
                    "record_count": row["total"],
                    "date_range": f"{row['first_order']} ~ {row['last_order']}",
                    "status": "completed",
                    "type": "seed",
                })

            # 预测写入记录
            cursor.execute(
                "SELECT MAX(created_at) AS last_fc, COUNT(*) AS total FROM sales_forecast"
            )
            fc = cursor.fetchone()
            if fc and fc["total"] > 0:
                records.append({
                    "source": "ml_pipeline (auto)",
                    "imported_at": fc["last_fc"].isoformat() if hasattr(fc["last_fc"], 'isoformat') else str(fc["last_fc"]),
                    "record_count": fc["total"],
                    "date_range": "future 7 days",
                    "status": "completed",
                    "type": "forecast",
                })

        conn.close()

        return jsonify({
            "success": True,
            "data": {"records": records},
            "message": "ok"
        }), 200
    except pymysql.MySQLError as e:
        return jsonify({
            "success": False, "data": None,
            "error": f"查询导入历史失败: {e}", "code": "DB_ERROR"
        }), 500


# ═══════════════════════════════════════════════════════════════
#  POST /api/admin/datasource/upload — 上传数据文件（预留）
# ═══════════════════════════════════════════════════════════════
@datasource_bp.route("/upload", methods=["POST"])
@jwt_required
@role_required("admin")
def upload_data():
    """
    上传 CSV/Excel 数据文件并导入 sales_record 表。

    当前为预留接口。完整实现需：
      1. 接收 multipart/form-data 文件
      2. 解析 CSV/Excel
      3. 校验字段格式
      4. 批量 INSERT 到 sales_record

    返回:
        501: {success: false, message: "上传功能预留，请使用 scripts/generate_mock_data.py 生成数据"}
    """
    return jsonify({
        "success": False,
        "data": None,
        "error": "上传功能预留，请使用 scripts/generate_mock_data.py 生成测试数据后执行 seed_data.sql 导入",
        "code": "NOT_IMPLEMENTED"
    }), 501
