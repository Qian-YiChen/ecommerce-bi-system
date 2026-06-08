"""
电商BI系统 — 后端主入口
======================
启动方式:
    D:\\Anaconda\\python.exe app.py

API 路由:
    认证: /api/auth/login  /api/auth/register  /api/auth/me
    数据: /api/data/query  /api/data/export     （苏文韬）
    预测: /api/predict/sales  /api/predict/stock （严辰乐集成薛淞模型）
    预警: /api/alert/rules  /api/alert/logs       （严辰乐）
    报表: /api/report/generate  /api/report/export （苏文韬）
"""

from flask import Flask, jsonify
from flask_cors import CORS

from config import get_config
from routes.auth_routes import auth_bp

config = get_config()


def create_app() -> Flask:
    """创建并配置 Flask 应用"""
    app = Flask(__name__)
    app.config["SECRET_KEY"] = config.JWT_SECRET_KEY
    app.config["DEBUG"] = config.DEBUG

    # CORS — 允许 Vue3 前端跨域访问
    CORS(app, origins=config.CORS_ORIGINS, supports_credentials=True)

    # 注册蓝图（路由模块）
    app.register_blueprint(auth_bp)

    # ── 后续注册（第4-8天）──
    # from routes.data_routes import data_bp       # 苏文韬
    # from routes.predict_routes import predict_bp  # 严辰乐
    # from routes.alert_routes import alert_bp      # 严辰乐
    # from routes.report_routes import report_bp    # 苏文韬
    # app.register_blueprint(data_bp)
    # app.register_blueprint(predict_bp)
    # app.register_blueprint(alert_bp)
    # app.register_blueprint(report_bp)

    # ── 健康检查 ──
    @app.route("/api/health")
    def health():
        return jsonify({"status": "ok", "service": "ecommerce-bi"})

    # ── 全局错误处理 ──
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "接口不存在", "code": "NOT_FOUND"}), 404

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"error": "服务器内部错误，已记录日志", "code": "SERVER_ERROR"}), 500

    return app


if __name__ == "__main__":
    app = create_app()
    print("=" * 60)
    print("  电商BI分析系统 — 后端服务")
    print(f"  地址: http://127.0.0.1:5000")
    print(f"  API:  http://127.0.0.1:5000/api/")
    print("=" * 60)
    app.run(host="127.0.0.1", port=5000, debug=config.DEBUG)
