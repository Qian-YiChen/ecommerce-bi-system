"""
预警与告警 API 路由
------------------
POST /api/alert/scan              — 手动触发异常扫描（UC-08）
GET  /api/alert/rules             — 获取预警规则列表
POST /api/alert/rules             — 创建预警规则（admin）
PUT  /api/alert/rules/<rule_id>   — 更新预警规则（admin）
GET  /api/alert/logs              — 获取预警日志（支持分页+筛选）
PUT  /api/alert/logs/<log_id>/resolve — 标记预警已处理

所有响应遵循统一格式：
    成功: {"success": true, "data": {...}, "message": "ok"}
    失败: {"success": false, "data": null, "error": "错误描述", "code": "ERROR_CODE"}
"""

from flask import Blueprint, request, jsonify, g
from middleware.jwt_middleware import jwt_required, role_required
from database.db_service import get_db_connection
import pymysql

alert_bp = Blueprint("alert", __name__, url_prefix="/api/alert")


# ═══════════════════════════════════════════════════════════════
#  辅助函数
# ═══════════════════════════════════════════════════════════════

def _row_to_dict(row):
    """将 pymysql DictCursor 行中的 datetime 转为 ISO 字符串"""
    if row is None:
        return None
    d = dict(row)
    for k, v in d.items():
        if hasattr(v, 'isoformat'):
            d[k] = v.isoformat()
    return d


# ═══════════════════════════════════════════════════════════════
#  异常扫描（UC-08 核心）
# ═══════════════════════════════════════════════════════════════

@alert_bp.route("/scan", methods=["POST"])
@jwt_required
def trigger_scan():
    """
    手动触发异常检测扫描（或由 APScheduler 定时调用）。

    调用 ml_pipeline.detect_anomalies_for_api() 扫描最近 30 天销售数据，
    与 alert_rule 中启用的规则对比，触发则写入 alert_log。

    返回:
        成功: {"success": true, "data": [...触发的告警列表...], "message": "扫描完成，触发 N 条告警"}
        无异常: {"success": true, "data": [], "message": "扫描完成，未发现异常"}
    """
    try:
        from ml.ml_pipeline import detect_anomalies_for_api
        alerts = detect_anomalies_for_api()
        count = len(alerts)
        return jsonify({
            "success": True,
            "data": alerts,
            "message": f"扫描完成，触发 {count} 条告警" if count else "扫描完成，未发现异常"
        }), 200
    except ImportError as e:
        return jsonify({
            "success": False, "data": None,
            "error": f"ML 模块导入失败: {e}",
            "code": "ML_IMPORT_ERROR"
        }), 500
    except Exception as e:
        return jsonify({
            "success": False, "data": None,
            "error": f"异常扫描失败: {e}",
            "code": "SCAN_ERROR"
        }), 500


# ═══════════════════════════════════════════════════════════════
#  预警规则 CRUD
# ═══════════════════════════════════════════════════════════════

@alert_bp.route("/rules", methods=["GET"])
@jwt_required
def list_rules():
    """
    获取预警规则列表。

    查询参数（可选）:
        is_enabled: 1=仅启用的, 0=仅禁用的, 不传=全部

    返回:
        {
            "success": true,
            "data": [
                {
                    "rule_id": 1,
                    "rule_name": "全品类销售额突降告警",
                    "rule_type": "sales_drop",
                    "threshold": -30.00,
                    "product_id": null,
                    "is_enabled": 1,
                    "created_at": "2026-06-08T00:00:00"
                },
                ...
            ],
            "message": "ok"
        }
    """
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            enabled_filter = request.args.get("is_enabled")
            if enabled_filter is not None:
                cursor.execute(
                    "SELECT * FROM alert_rule WHERE is_enabled = %s ORDER BY rule_id",
                    (int(enabled_filter),)
                )
            else:
                cursor.execute("SELECT * FROM alert_rule ORDER BY rule_id")
            rows = cursor.fetchall()
        conn.close()

        rules = [_row_to_dict(r) for r in rows]
        return jsonify({
            "success": True,
            "data": rules,
            "message": "ok"
        }), 200
    except pymysql.MySQLError as e:
        return jsonify({
            "success": False, "data": None,
            "error": f"查询预警规则失败: {e}",
            "code": "DB_ERROR"
        }), 500


@alert_bp.route("/rules", methods=["POST"])
@jwt_required
@role_required("admin")
def create_rule():
    """
    创建预警规则（仅管理员）。

    请求体:
        {
            "rule_name": "string",      # 必填，规则名称
            "rule_type": "string",      # 必填，sales_drop | stock_low | return_spike
            "threshold": -30.00,        # 必填，触发阈值（百分比）
            "product_id": null,         # 可选，适用商品ID，null=全局
            "is_enabled": 1             # 可选，默认 1
        }

    返回:
        成功: {"success": true, "data": {"rule_id": 4}, "message": "预警规则创建成功"}
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({
            "success": False, "data": None,
            "error": "请提供 JSON 请求体", "code": "BAD_REQUEST"
        }), 400

    rule_name = data.get("rule_name", "").strip()
    rule_type = data.get("rule_type", "").strip()
    threshold = data.get("threshold")

    if not rule_name or not rule_type or threshold is None:
        return jsonify({
            "success": False, "data": None,
            "error": "rule_name、rule_type 和 threshold 为必填字段",
            "code": "VALIDATION_ERROR"
        }), 400

    valid_types = ("sales_drop", "stock_low", "return_spike")
    if rule_type not in valid_types:
        return jsonify({
            "success": False, "data": None,
            "error": f"无效的 rule_type: {rule_type}，可选值：{valid_types}",
            "code": "VALIDATION_ERROR"
        }), 400

    product_id = data.get("product_id")  # None = 全局规则
    is_enabled = data.get("is_enabled", 1)

    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO alert_rule (rule_name, rule_type, threshold, product_id, is_enabled) "
                "VALUES (%s, %s, %s, %s, %s)",
                (rule_name, rule_type, threshold, product_id, is_enabled)
            )
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()

        return jsonify({
            "success": True,
            "data": {"rule_id": new_id},
            "message": "预警规则创建成功"
        }), 201
    except pymysql.MySQLError as e:
        return jsonify({
            "success": False, "data": None,
            "error": f"创建预警规则失败: {e}",
            "code": "DB_ERROR"
        }), 500


@alert_bp.route("/rules/<int:rule_id>", methods=["PUT"])
@jwt_required
@role_required("admin")
def update_rule(rule_id):
    """
    更新预警规则（仅管理员）。

    请求体（所有字段可选，只更新提供的字段）:
        {
            "rule_name": "string",
            "rule_type": "string",
            "threshold": -30.00,
            "product_id": null,
            "is_enabled": 1
        }

    返回:
        成功: {"success": true, "data": null, "message": "预警规则更新成功"}
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({
            "success": False, "data": None,
            "error": "请提供 JSON 请求体", "code": "BAD_REQUEST"
        }), 400

    # 只构建提供的字段
    allowed_fields = ["rule_name", "rule_type", "threshold", "product_id", "is_enabled"]
    updates = {}
    for field in allowed_fields:
        if field in data:
            updates[field] = data[field]

    if not updates:
        return jsonify({
            "success": False, "data": None,
            "error": "未提供任何要更新的字段", "code": "VALIDATION_ERROR"
        }), 400

    if "rule_type" in updates and updates["rule_type"] not in ("sales_drop", "stock_low", "return_spike"):
        return jsonify({
            "success": False, "data": None,
            "error": f"无效的 rule_type: {updates['rule_type']}",
            "code": "VALIDATION_ERROR"
        }), 400

    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # 先检查规则是否存在
            cursor.execute("SELECT 1 FROM alert_rule WHERE rule_id = %s", (rule_id,))
            if cursor.fetchone() is None:
                conn.close()
                return jsonify({
                    "success": False, "data": None,
                    "error": f"预警规则 {rule_id} 不存在",
                    "code": "NOT_FOUND"
                }), 404

            # 动态构建 UPDATE
            set_clause = ", ".join(f"{k} = %s" for k in updates)
            values = list(updates.values())
            values.append(rule_id)
            cursor.execute(
                f"UPDATE alert_rule SET {set_clause} WHERE rule_id = %s",
                values
            )
        conn.commit()
        conn.close()

        return jsonify({
            "success": True, "data": None,
            "message": "预警规则更新成功"
        }), 200
    except pymysql.MySQLError as e:
        return jsonify({
            "success": False, "data": None,
            "error": f"更新预警规则失败: {e}",
            "code": "DB_ERROR"
        }), 500


# ═══════════════════════════════════════════════════════════════
#  预警日志查询 & 处理
# ═══════════════════════════════════════════════════════════════

@alert_bp.route("/logs", methods=["GET"])
@jwt_required
def list_logs():
    """
    获取预警日志列表（支持分页 + 筛选）。

    查询参数（可选）:
        page:     页码，默认 1
        per_page: 每页条数，默认 20，最大 100
        status:   按状态筛选：pending | resolved | ignored
        severity: 按严重程度筛选：red | orange | yellow

    返回:
        {
            "success": true,
            "data": {
                "logs": [...],
                "pagination": {
                    "page": 1,
                    "per_page": 20,
                    "total": 5,
                    "total_pages": 1
                }
            },
            "message": "ok"
        }
    """
    try:
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 20, type=int)
        status_filter = request.args.get("status")
        severity_filter = request.args.get("severity")

        # 参数校验
        page = max(1, page)
        per_page = max(1, min(100, per_page))

        conn = get_db_connection()

        # 构建 WHERE 条件
        where_clauses = []
        params = []
        if status_filter:
            where_clauses.append("al.status = %s")
            params.append(status_filter)
        if severity_filter:
            where_clauses.append("al.severity = %s")
            params.append(severity_filter)

        where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        # 查询总数
        with conn.cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) AS total FROM alert_log al{where_sql}", params)
            total = cursor.fetchone()["total"]

        # 查询当前页
        offset = (page - 1) * per_page
        with conn.cursor() as cursor:
            cursor.execute(
                f"SELECT al.*, ar.rule_name "
                f"FROM alert_log al "
                f"JOIN alert_rule ar ON al.rule_id = ar.rule_id"
                f"{where_sql} "
                f"ORDER BY al.trigger_time DESC "
                f"LIMIT %s OFFSET %s",
                params + [per_page, offset]
            )
            rows = cursor.fetchall()

        conn.close()

        logs = [_row_to_dict(r) for r in rows]
        total_pages = max(1, (total + per_page - 1) // per_page)

        return jsonify({
            "success": True,
            "data": {
                "logs": logs,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": total,
                    "total_pages": total_pages
                }
            },
            "message": "ok"
        }), 200
    except pymysql.MySQLError as e:
        return jsonify({
            "success": False, "data": None,
            "error": f"查询预警日志失败: {e}",
            "code": "DB_ERROR"
        }), 500


@alert_bp.route("/logs/<int:log_id>/resolve", methods=["PUT"])
@jwt_required
def resolve_log(log_id):
    """
    标记预警为已处理。

    请求体（可选）:
        {}  — 无需额外参数，当前登录用户自动作为处理人

    返回:
        成功: {"success": true, "data": null, "message": "预警已标记为已处理"}
        未找到: {"success": false, "data": null, "error": "预警日志 999 不存在", "code": "NOT_FOUND"}
    """
    try:
        conn = get_db_connection()

        # 先检查日志是否存在及当前状态
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT log_id, status FROM alert_log WHERE log_id = %s",
                (log_id,)
            )
            row = cursor.fetchone()

        if row is None:
            conn.close()
            return jsonify({
                "success": False, "data": None,
                "error": f"预警日志 {log_id} 不存在",
                "code": "NOT_FOUND"
            }), 404

        if row["status"] == "resolved":
            conn.close()
            return jsonify({
                "success": False, "data": None,
                "error": "该预警已处理，无需重复操作",
                "code": "ALREADY_RESOLVED"
            }), 409

        # 标记为已处理
        resolver_id = g.current_user["user_id"]
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE alert_log SET status = 'resolved', resolved_by = %s, "
                "resolved_at = NOW() WHERE log_id = %s",
                (resolver_id, log_id)
            )
        conn.commit()
        conn.close()

        return jsonify({
            "success": True, "data": None,
            "message": "预警已标记为已处理"
        }), 200
    except pymysql.MySQLError as e:
        return jsonify({
            "success": False, "data": None,
            "error": f"处理预警失败: {e}",
            "code": "DB_ERROR"
        }), 500
