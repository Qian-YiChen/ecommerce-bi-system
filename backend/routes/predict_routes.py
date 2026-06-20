"""
预测相关 API 路由
----------------
GET  /api/predict/sales  — 获取最新销售预测结果（UC-02）
GET  /api/predict/stock  — 获取库存补货建议（UC-03）

对接薛淞 ml/ml_pipeline.py 中的 API 函数：
    predict_sales_for_api()  — 返回 24 商品 × 7 天 = 168 条预测
    predict_stock_for_api()  — 返回每商品补货建议

所有响应遵循统一格式：
    成功: {"success": true, "data": {...}, "message": "ok"}
    失败: {"success": false, "data": null, "error": "错误描述", "code": "ERROR_CODE"}
"""

from flask import Blueprint, jsonify
from middleware.jwt_middleware import jwt_required

predict_bp = Blueprint("predict", __name__, url_prefix="/api/predict")


@predict_bp.route("/sales", methods=["GET"])
@jwt_required
def get_sales_forecast():
    """
    获取最新销售预测结果（未来 7 天，24 个商品）。

    返回:
        {
            "success": true,
            "data": [
                {
                    "product_id": 1,
                    "product_name": "纯棉简约T恤女",
                    "forecast_date": "2026-06-21",
                    "predicted_quantity": 15,
                    "model_type": "linear"
                },
                ...  // 24 商品 × 7 天 = 最多 168 条
            ],
            "message": "ok"
        }
    """
    try:
        from ml.ml_pipeline import predict_sales_for_api
        predictions = predict_sales_for_api()
        return jsonify({
            "success": True,
            "data": predictions,
            "message": "ok"
        }), 200
    except FileNotFoundError as e:
        return jsonify({
            "success": False, "data": None,
            "error": f"模型文件未找到，请先训练模型: {e}",
            "code": "MODEL_NOT_FOUND"
        }), 500
    except ImportError as e:
        return jsonify({
            "success": False, "data": None,
            "error": f"ML 模块导入失败: {e}",
            "code": "ML_IMPORT_ERROR"
        }), 500
    except Exception as e:
        return jsonify({
            "success": False, "data": None,
            "error": f"销售预测失败: {e}",
            "code": "PREDICT_ERROR"
        }), 500


@predict_bp.route("/stock", methods=["GET"])
@jwt_required
def get_stock_suggestions():
    """
    获取库存补货建议（基于 sales_forecast + product.stock_quantity）。

    返回:
        {
            "success": true,
            "data": [
                {
                    "product_id": 1,
                    "product_name": "纯棉简约T恤女",
                    "current_stock": 80,
                    "demand_next_3_days": 12,
                    "safety_stock": 6,
                    "suggest_replenish": 0
                },
                ...
            ],
            "message": "ok"
        }

    说明:
        - current_stock 来自 product.stock_quantity（数据库真实值）
        - suggest_replenish = 0 表示库存充足，无需补货
        - 安全库存模型：95% 服务水平，z=1.65，提前期=3天
    """
    try:
        from ml.ml_pipeline import predict_stock_for_api
        results = predict_stock_for_api()
        return jsonify({
            "success": True,
            "data": results,
            "message": "ok"
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
            "error": f"库存预测失败: {e}",
            "code": "STOCK_ERROR"
        }), 500
