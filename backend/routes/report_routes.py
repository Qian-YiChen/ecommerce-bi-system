"""
报表导出 API 路由（UC-09）
-------------------------
POST /api/report/generate          — 生成报表文件
GET  /api/report/download/<filename> — 下载已生成的报表

所有响应遵循统一格式（参见 docs/函数参数需求文档.md §4.1）：
  成功: {"success": true, "data": {...}, "message": "操作成功"}
  失败: {"success": false, "data": null, "error": "错误描述", "code": "ERROR_CODE"}

作者: 苏文韬
日期: 2026-06-09
"""

import os
from flask import Blueprint, request, jsonify, send_file
from middleware.jwt_middleware import jwt_required
from database.db_service import export_report

report_bp = Blueprint("report", __name__, url_prefix="/api/report")


@report_bp.route("/generate", methods=["POST"])
@jwt_required
def generate_report():
    """
    生成报表文件（UC-09）

    请求体:
        {
            "report_type": "daily",         # "daily" | "weekly" | "monthly" | "custom"
            "format": "excel",              # "excel" | "csv"
            "params": {
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "region": null,
                "category_id": null,
                "channel": null,
                "group_by": "day"
            }
        }

    成功响应:
        {
            "success": true,
            "data": {
                "filename": "report_daily_20260609_153000.xlsx",
                "download_url": "/api/report/download/report_daily_20260609_153000.xlsx"
            },
            "message": "报表生成成功"
        }

    失败响应:
        {
            "success": false,
            "data": null,
            "error": "无效的 report_type: yearly，可选值：...",
            "code": "VALIDATION_ERROR"
        }
    """
    body = request.get_json(silent=True)
    if not body:
        return jsonify({
            "success": False, "data": None,
            "error": "请提供 JSON 请求体", "code": "BAD_REQUEST"
        }), 400

    report_type = body.get("report_type", "").strip()
    export_format = body.get("format", "excel").strip()
    params = body.get("params", {})

    # ── 参数校验 ──
    valid_types = ("daily", "weekly", "monthly", "custom")
    if report_type not in valid_types:
        return jsonify({
            "success": False, "data": None,
            "error": f"无效的 report_type: {report_type}，可选值：{valid_types}",
            "code": "VALIDATION_ERROR"
        }), 400

    valid_formats = ("excel", "csv")
    if export_format not in valid_formats:
        return jsonify({
            "success": False, "data": None,
            "error": f"不支持的导出格式: {export_format}，可选值：{valid_formats}",
            "code": "VALIDATION_ERROR"
        }), 400

    if not params.get("start_date") or not params.get("end_date"):
        return jsonify({
            "success": False, "data": None,
            "error": "params 中缺少必填字段 start_date 或 end_date",
            "code": "VALIDATION_ERROR"
        }), 400

    # ── 调用苏文韬的 export_report ──
    try:
        filepath = export_report(
            report_type=report_type,
            params=params,
            format=export_format,
        )
    except ValueError as e:
        return jsonify({
            "success": False, "data": None,
            "error": str(e), "code": "VALIDATION_ERROR"
        }), 400
    except ImportError as e:
        return jsonify({
            "success": False, "data": None,
            "error": str(e), "code": "DEPENDENCY_MISSING"
        }), 500
    except RuntimeError as e:
        return jsonify({
            "success": False, "data": None,
            "error": str(e), "code": "DATABASE_ERROR"
        }), 500

    filename = os.path.basename(filepath)

    return jsonify({
        "success": True,
        "data": {
            "filename": filename,
            "download_url": f"/api/report/download/{filename}",
        },
        "message": "报表生成成功"
    }), 200


@report_bp.route("/download/<filename>", methods=["GET"])
@jwt_required
def download_report(filename: str):
    """
    下载已生成的报表文件

    路径参数:
        filename — 报表文件名（不含路径），如 "report_daily_20260609_153000.xlsx"

    成功:
        返回文件流（Content-Disposition: attachment）

    失败响应:
        {
            "success": false,
            "data": null,
            "error": "文件不存在: report_xxx.xlsx",
            "code": "NOT_FOUND"
        }
    """
    import tempfile

    # 安全检查：防止路径穿越
    safe_filename = os.path.basename(filename)
    if safe_filename != filename:
        return jsonify({
            "success": False, "data": None,
            "error": "文件名包含非法字符", "code": "VALIDATION_ERROR"
        }), 400

    filepath = os.path.join(tempfile.gettempdir(), safe_filename)

    if not os.path.exists(filepath):
        return jsonify({
            "success": False, "data": None,
            "error": f"文件不存在: {safe_filename}", "code": "NOT_FOUND"
        }), 404

    # 根据扩展名设置 MIME 类型
    mime_map = {
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".csv": "text/csv; charset=utf-8",
    }
    ext = os.path.splitext(safe_filename)[1].lower()
    mimetype = mime_map.get(ext, "application/octet-stream")

    return send_file(
        filepath,
        mimetype=mimetype,
        as_attachment=True,
        download_name=safe_filename,
    )
