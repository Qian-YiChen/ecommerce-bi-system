"""
预测 & 预警路由集成测试
=====================
验证 predict_routes.py + alert_routes.py 的 API 路由注册和行为。
使用 mock 替代 ML 模型和数据库，无需 MySQL。
"""
import sys
import io
import json
from unittest.mock import patch, MagicMock

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# ── 确保可用工程根导入 ml/ ──
import os
_sys_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _sys_root not in sys.path:
    sys.path.insert(0, _sys_root)

from app import create_app

# ============================================================
# Mock data
# ============================================================

MOCK_SALES_FORECAST = [
    {
        "product_id": 1, "product_name": "纯棉简约T恤女",
        "forecast_date": "2026-06-21", "predicted_quantity": 15,
        "model_type": "linear"
    },
    {
        "product_id": 2, "product_name": "法式碎花连衣裙",
        "forecast_date": "2026-06-21", "predicted_quantity": 8,
        "model_type": "linear"
    },
]

MOCK_STOCK_RESULTS = [
    {
        "product_id": 1, "product_name": "纯棉简约T恤女",
        "current_stock": 80, "demand_next_3_days": 12,
        "safety_stock": 6, "suggest_replenish": 0
    },
    {
        "product_id": 2, "product_name": "法式碎花连衣裙",
        "current_stock": 120, "demand_next_3_days": 25,
        "safety_stock": 8, "suggest_replenish": 5
    },
]

MOCK_ANOMALIES = [
    {
        "rule_id": 1, "rule_type": "sales_drop",
        "content": "全品类销售额较前7日均线下降35.2%...",
        "severity": "yellow", "anomaly_value": -35.2,
        "baseline_value": 50000.0
    },
]

MOCK_ALERT_RULES = [
    {
        "rule_id": 1, "rule_name": "全品类销售额突降告警",
        "rule_type": "sales_drop", "threshold": -30.0,
        "product_id": None, "is_enabled": 1,
        "created_at": "2026-06-08T00:00:00"
    },
    {
        "rule_id": 2, "rule_name": "库存安全警戒线",
        "rule_type": "stock_low", "threshold": 20.0,
        "product_id": None, "is_enabled": 1,
        "created_at": "2026-06-08T00:00:00"
    },
]

MOCK_ALERT_LOGS = [
    {
        "log_id": 1, "rule_id": 1, "rule_name": "全品类销售额突降告警",
        "trigger_time": "2026-06-20T10:00:00",
        "alert_content": "全品类销售额较前7日均线下降32.5%",
        "anomaly_value": -32.5, "baseline_value": 45000.0,
        "severity": "orange", "status": "pending",
        "resolved_by": None, "resolved_at": None
    },
]


# ============================================================
# Mock helpers
# ============================================================

def mock_get_user(username):
    """Simulate db_service.get_user_by_username"""
    from models.user import User
    from auth.auth_service import hash_password
    if username == "admin":
        return User(user_id=1, username="admin",
                    password_hash=hash_password("admin123"),
                    role="admin", status=1)
    if username == "viewer":
        return User(user_id=2, username="viewer",
                    password_hash=hash_password("viewer123"),
                    role="viewer", status=1)
    return None


def _login_as(app, role="admin"):
    """Helper: login and return token + client"""
    from database.db_service import get_user_by_username
    with patch("database.db_service.get_user_by_username", side_effect=mock_get_user):
        with app.test_client() as client:
            username = "admin" if role == "admin" else "viewer"
            password = "admin123" if role == "admin" else "viewer123"
            resp = client.post("/api/auth/login",
                data=json.dumps({"username": username, "password": password}),
                content_type="application/json")
            token = resp.get_json()["data"]["token"]
            return client, token


# ============================================================
# Test Suite
# ============================================================

passed = 0
failed = 0

def test(name):
    global passed, failed
    print(f"\n[{name}]")

def check(condition, msg):
    global passed, failed
    if condition:
        print(f"  PASS: {msg}")
        passed += 1
    else:
        print(f"  FAIL: {msg}")
        failed += 1


print("=" * 60)
print("  Predict & Alert Routes Integration Test Suite")
print("=" * 60)

# ── Create app once ──
app = create_app()

# ============================================================
# TEST 1: Route registration
# ============================================================
test("TEST 1: New route registration")
routes = {}
for r in app.url_map.iter_rules():
    methods = sorted(m for m in r.methods if m not in ("HEAD", "OPTIONS"))
    if methods:
        routes[r.rule] = methods

# Flask 将同一路径的不同 HTTP 方法注册为独立规则
# 用 "path:method1,method2" 集合避免字典键冲突
routes_set = set()
for r in app.url_map.iter_rules():
    methods = sorted(m for m in r.methods if m not in ("HEAD", "OPTIONS"))
    if methods:
        routes_set.add(f"{r.rule}:{','.join(methods)}")

expected_routes = [
    ("/api/predict/sales", ["GET"]),
    ("/api/predict/stock", ["GET"]),
    ("/api/alert/scan", ["POST"]),
    ("/api/alert/rules", ["GET"]),
    ("/api/alert/rules", ["POST"]),
    ("/api/alert/rules/<int:rule_id>", ["PUT"]),
    ("/api/alert/logs", ["GET"]),
    ("/api/alert/logs/<int:log_id>/resolve", ["PUT"]),
]
for path, methods in expected_routes:
    key = f"{path}:{','.join(methods)}"
    found = key in routes_set
    check(found, f"{path} {methods}")

# ============================================================
# TEST 2: Predict routes — auth check (no token)
# ============================================================
test("TEST 2: Predict routes — require auth")
with app.test_client() as client:
    resp = client.get("/api/predict/sales")
    check(resp.status_code == 401, f"GET /api/predict/sales (no token) -> 401")
    check(resp.get_json()["code"] == "TOKEN_MISSING", "returns TOKEN_MISSING")

    resp = client.get("/api/predict/stock")
    check(resp.status_code == 401, f"GET /api/predict/stock (no token) -> 401")

# ============================================================
# TEST 3: Predict routes — mock ML success
# ============================================================
test("TEST 3: Predict /sales — mock ML success")
with patch("ml.ml_pipeline.predict_sales_for_api", return_value=MOCK_SALES_FORECAST):
    with patch("database.db_service.get_user_by_username", side_effect=mock_get_user):
        with app.test_client() as client:
            client2, token = _login_as(app, "admin")
            resp = client2.get("/api/predict/sales",
                headers={"Authorization": f"Bearer {token}"})
            check(resp.status_code == 200, "GET /api/predict/sales -> 200")
            body = resp.get_json()
            check(body["success"] is True, "success=True")
            check(len(body["data"]) == 2, f"2 predictions returned, got {len(body['data'])}")
            check(body["data"][0]["product_name"] == "纯棉简约T恤女",
                  f"product_name={body['data'][0]['product_name']}")

test("TEST 3b: Predict /stock — mock ML success")
with patch("ml.ml_pipeline.predict_stock_for_api", return_value=MOCK_STOCK_RESULTS):
    with patch("database.db_service.get_user_by_username", side_effect=mock_get_user):
        with app.test_client() as client:
            client2, token = _login_as(app, "admin")
            resp = client2.get("/api/predict/stock",
                headers={"Authorization": f"Bearer {token}"})
            check(resp.status_code == 200, "GET /api/predict/stock -> 200")
            body = resp.get_json()
            check(body["success"] is True, "success=True")
            check(len(body["data"]) == 2, f"2 stock suggestions, got {len(body['data'])}")
            check("suggest_replenish" in body["data"][0], "has suggest_replenish field")

# ============================================================
# TEST 4: Alert scan — mock ML
# ============================================================
test("TEST 4: POST /api/alert/scan — trigger anomaly scan")
with patch("ml.ml_pipeline.detect_anomalies_for_api", return_value=MOCK_ANOMALIES):
    with patch("database.db_service.get_user_by_username", side_effect=mock_get_user):
        with app.test_client() as client:
            client2, token = _login_as(app, "admin")
            resp = client2.post("/api/alert/scan",
                headers={"Authorization": f"Bearer {token}"})
            check(resp.status_code == 200, "POST /api/alert/scan -> 200")
            body = resp.get_json()
            check(body["success"] is True, "success=True")
            check(len(body["data"]) == 1, f"1 anomaly detected, got {len(body['data'])}")
            check("触发 1 条告警" in body["message"], "message indicates 1 alert")

test("TEST 4b: Alert scan — auth check")
with app.test_client() as client:
    resp = client.post("/api/alert/scan")
    check(resp.status_code == 401, "POST /api/alert/scan (no token) -> 401")

# ============================================================
# TEST 5: Alert scan — empty result (no anomalies)
# ============================================================
test("TEST 5: Alert scan — no anomalies")
with patch("ml.ml_pipeline.detect_anomalies_for_api", return_value=[]):
    with patch("database.db_service.get_user_by_username", side_effect=mock_get_user):
        with app.test_client() as client:
            client2, token = _login_as(app, "admin")
            resp = client2.post("/api/alert/scan",
                headers={"Authorization": f"Bearer {token}"})
            check(resp.status_code == 200, "POST /api/alert/scan -> 200")
            body = resp.get_json()
            check(body["success"] is True, "success=True")
            check(body["data"] == [], "empty data array")
            check("未发现异常" in body["message"], "message says no anomalies")

# ============================================================
# TEST 6: Alert rules — LIST (mocked DB)
# ============================================================
test("TEST 6: GET /api/alert/rules — list rules")
mock_conn = MagicMock()
mock_cursor = MagicMock()
mock_conn.__enter__ = MagicMock(return_value=mock_conn)  # for 'with conn:'
mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
mock_cursor.fetchall.return_value = [
    {"rule_id": 1, "rule_name": "全品类销售额突降告警", "rule_type": "sales_drop",
     "threshold": -30.0, "product_id": None, "is_enabled": 1,
     "created_at": "2026-06-08 00:00:00"},
    {"rule_id": 2, "rule_name": "库存安全警戒线", "rule_type": "stock_low",
     "threshold": 20.0, "product_id": None, "is_enabled": 1,
     "created_at": "2026-06-08 00:00:00"},
]

with patch("routes.alert_routes.get_db_connection", return_value=mock_conn):
    # Mock conn.cursor() to return our mock cursor
    mock_conn.cursor.return_value = mock_cursor
    with patch("database.db_service.get_user_by_username", side_effect=mock_get_user):
        with app.test_client() as client:
            client2, token = _login_as(app, "admin")
            resp = client2.get("/api/alert/rules",
                headers={"Authorization": f"Bearer {token}"})
            check(resp.status_code == 200, "GET /api/alert/rules -> 200")
            body = resp.get_json()
            check(body["success"] is True, "success=True")
            check(len(body["data"]) == 2, f"2 rules returned, got {len(body['data'])}")

# ============================================================
# TEST 7: Alert rules — CREATE (requires admin)
# ============================================================
test("TEST 7: POST /api/alert/rules — create rule (admin)")
# Need to mock the insert + lastrowid
mock_conn2 = MagicMock()
mock_cursor2 = MagicMock()
mock_cursor2.__enter__ = MagicMock(return_value=mock_cursor2)
mock_cursor2.lastrowid = 4
mock_conn2.__enter__ = MagicMock(return_value=mock_conn2)
mock_conn2.cursor.return_value = mock_cursor2

with patch("routes.alert_routes.get_db_connection", return_value=mock_conn2):
    with patch("database.db_service.get_user_by_username", side_effect=mock_get_user):
        with app.test_client() as client:
            client2, token = _login_as(app, "admin")
            resp = client2.post("/api/alert/rules",
                data=json.dumps({
                    "rule_name": "测试规则", "rule_type": "sales_drop",
                    "threshold": -15.0
                }),
                content_type="application/json",
                headers={"Authorization": f"Bearer {token}"})
            check(resp.status_code == 201, "POST /api/alert/rules -> 201")
            body = resp.get_json()
            check(body["success"] is True, "success=True")
            check(body["data"]["rule_id"] == 4, f"rule_id=4, got {body['data']['rule_id']}")

test("TEST 7b: POST /api/alert/rules — non-admin rejected")
with patch("database.db_service.get_user_by_username", side_effect=mock_get_user):
    with app.test_client() as client:
        client2, token = _login_as(app, "viewer")
        resp = client2.post("/api/alert/rules",
            data=json.dumps({"rule_name": "x", "rule_type": "sales_drop", "threshold": -10}),
            content_type="application/json",
            headers={"Authorization": f"Bearer {token}"})
        check(resp.status_code == 403, f"viewer POST /rules -> 403")
        check(resp.get_json()["code"] == "FORBIDDEN", "returns FORBIDDEN")

test("TEST 7c: POST /api/alert/rules — validation")
with patch("database.db_service.get_user_by_username", side_effect=mock_get_user):
    with app.test_client() as client:
        client2, token = _login_as(app, "admin")
        # missing fields
        resp = client2.post("/api/alert/rules",
            data=json.dumps({}), content_type="application/json",
            headers={"Authorization": f"Bearer {token}"})
        check(resp.status_code == 400, "empty body -> 400")
        check(resp.get_json()["code"] == "BAD_REQUEST", "BAD_REQUEST")

# ============================================================
# TEST 8: Alert rules — UPDATE (admin)
# ============================================================
test("TEST 8: PUT /api/alert/rules/<id> — update rule")

def mock_update_conn():
    """Mock that simulates finding rule_id=1 and updating it"""
    conn = MagicMock()
    conn.__enter__ = MagicMock(return_value=conn)
    cursor = MagicMock()
    cursor.__enter__ = MagicMock(return_value=cursor)
    # First call: SELECT check → row exists
    cursor.fetchone.side_effect = [{"1": 1}, None]  # exists, then done
    conn.cursor.return_value = cursor
    return conn

with patch("routes.alert_routes.get_db_connection", side_effect=[mock_update_conn()]):
    with patch("database.db_service.get_user_by_username", side_effect=mock_get_user):
        with app.test_client() as client:
            client2, token = _login_as(app, "admin")
            resp = client2.put("/api/alert/rules/1",
                data=json.dumps({"is_enabled": 0}),
                content_type="application/json",
                headers={"Authorization": f"Bearer {token}"})
            check(resp.status_code == 200, "PUT /api/alert/rules/1 -> 200")
            check(resp.get_json()["success"] is True, "success=True")

test("TEST 8b: PUT /api/alert/rules/<id> — non-admin rejected")
with patch("database.db_service.get_user_by_username", side_effect=mock_get_user):
    with app.test_client() as client:
        client2, token = _login_as(app, "viewer")
        resp = client2.put("/api/alert/rules/1",
            data=json.dumps({"is_enabled": 0}), content_type="application/json",
            headers={"Authorization": f"Bearer {token}"})
        check(resp.status_code == 403, f"viewer PUT /rules/1 -> 403")

# ============================================================
# TEST 9: Alert logs — LIST (mocked DB)
# ============================================================
test("TEST 9: GET /api/alert/logs — list logs")

def mock_logs_conn():
    conn = MagicMock()
    conn.__enter__ = MagicMock(return_value=conn)
    cursor1 = MagicMock()
    cursor1.__enter__ = MagicMock(return_value=cursor1)
    cursor1.fetchone.return_value = {"total": 2}
    cursor2 = MagicMock()
    cursor2.__enter__ = MagicMock(return_value=cursor2)
    cursor2.fetchall.return_value = [
        {"log_id": 1, "rule_id": 1, "rule_name": "全品类销售额突降告警",
         "trigger_time": "2026-06-20 10:00:00",
         "alert_content": "销售额下降32.5%", "anomaly_value": -32.5,
         "baseline_value": 45000.0, "severity": "orange",
         "status": "pending", "resolved_by": None, "resolved_at": None},
        {"log_id": 2, "rule_id": 2, "rule_name": "库存安全警戒线",
         "trigger_time": "2026-06-20 09:00:00",
         "alert_content": "库存低于安全线", "anomaly_value": 18.0,
         "baseline_value": 150.0, "severity": "yellow",
         "status": "resolved", "resolved_by": 1,
         "resolved_at": "2026-06-20 09:30:00"},
    ]
    conn.cursor.side_effect = [cursor1, cursor2]
    return conn

with patch("routes.alert_routes.get_db_connection", side_effect=[mock_logs_conn()]):
    with patch("database.db_service.get_user_by_username", side_effect=mock_get_user):
        with app.test_client() as client:
            client2, token = _login_as(app, "admin")
            resp = client2.get("/api/alert/logs",
                headers={"Authorization": f"Bearer {token}"})
            check(resp.status_code == 200, "GET /api/alert/logs -> 200")
            body = resp.get_json()
            check(body["success"] is True, "success=True")
            check(len(body["data"]["logs"]) == 2, f"2 logs returned")
            check(body["data"]["pagination"]["total"] == 2, "pagination total=2")
            check(body["data"]["pagination"]["total_pages"] == 1, "total_pages=1")

# ============================================================
# TEST 10: Alert logs — RESOLVE
# ============================================================
test("TEST 10: PUT /api/alert/logs/<id>/resolve — mark resolved")

def mock_resolve_conn():
    conn = MagicMock()
    conn.__enter__ = MagicMock(return_value=conn)
    cursor = MagicMock()
    cursor.__enter__ = MagicMock(return_value=cursor)
    cursor.fetchone.return_value = {"log_id": 1, "status": "pending"}
    conn.cursor.return_value = cursor
    return conn

with patch("routes.alert_routes.get_db_connection", side_effect=[mock_resolve_conn()]):
    with patch("database.db_service.get_user_by_username", side_effect=mock_get_user):
        with app.test_client() as client:
            client2, token = _login_as(app, "admin")
            resp = client2.put("/api/alert/logs/1/resolve",
                headers={"Authorization": f"Bearer {token}"})
            check(resp.status_code == 200, "PUT /api/alert/logs/1/resolve -> 200")
            check(resp.get_json()["success"] is True, "success=True")
            check("已标记为已处理" in resp.get_json()["message"], "marked resolved")

test("TEST 10b: Alert logs — resolve non-existent")

def mock_resolve_nonexist():
    conn = MagicMock()
    conn.__enter__ = MagicMock(return_value=conn)
    cursor = MagicMock()
    cursor.__enter__ = MagicMock(return_value=cursor)
    cursor.fetchone.return_value = None  # Not found
    conn.cursor.return_value = cursor
    return conn

with patch("routes.alert_routes.get_db_connection", side_effect=[mock_resolve_nonexist()]):
    with patch("database.db_service.get_user_by_username", side_effect=mock_get_user):
        with app.test_client() as client:
            client2, token = _login_as(app, "admin")
            resp = client2.put("/api/alert/logs/999/resolve",
                headers={"Authorization": f"Bearer {token}"})
            check(resp.status_code == 404, "PUT /api/alert/logs/999/resolve -> 404")
            check(resp.get_json()["code"] == "NOT_FOUND", "NOT_FOUND")

test("TEST 10c: Alert logs — resolve already resolved")

def mock_resolve_already():
    conn = MagicMock()
    conn.__enter__ = MagicMock(return_value=conn)
    cursor = MagicMock()
    cursor.__enter__ = MagicMock(return_value=cursor)
    cursor.fetchone.return_value = {"log_id": 1, "status": "resolved"}
    conn.cursor.return_value = cursor
    return conn

with patch("routes.alert_routes.get_db_connection", side_effect=[mock_resolve_already()]):
    with patch("database.db_service.get_user_by_username", side_effect=mock_get_user):
        with app.test_client() as client:
            client2, token = _login_as(app, "admin")
            resp = client2.put("/api/alert/logs/1/resolve",
                headers={"Authorization": f"Bearer {token}"})
            check(resp.status_code == 409, "PUT /api/alert/logs/1/resolve (already) -> 409")
            check(resp.get_json()["code"] == "ALREADY_RESOLVED", "ALREADY_RESOLVED")

# ============================================================
# TEST 11: Alert scan — ML error handling
# ============================================================
test("TEST 11: Alert scan — ML error")
with patch("ml.ml_pipeline.detect_anomalies_for_api", side_effect=RuntimeError("DB连接失败")):
    with patch("database.db_service.get_user_by_username", side_effect=mock_get_user):
        with app.test_client() as client:
            client2, token = _login_as(app, "admin")
            resp = client2.post("/api/alert/scan",
                headers={"Authorization": f"Bearer {token}"})
            check(resp.status_code == 500, "POST /api/alert/scan (error) -> 500")
            check(resp.get_json()["success"] is False, "success=False")
            check(resp.get_json()["code"] == "SCAN_ERROR", "SCAN_ERROR")

# ============================================================
# TEST 12: Predict routes — ML error handling
# ============================================================
test("TEST 12: Predict /sales — model not found")
with patch("ml.ml_pipeline.predict_sales_for_api",
           side_effect=FileNotFoundError("models/sales_lr_baseline.pkl not found")):
    with patch("database.db_service.get_user_by_username", side_effect=mock_get_user):
        with app.test_client() as client:
            client2, token = _login_as(app, "admin")
            resp = client2.get("/api/predict/sales",
                headers={"Authorization": f"Bearer {token}"})
            check(resp.status_code == 500, "GET /sales (no model) -> 500")
            check(resp.get_json()["code"] == "MODEL_NOT_FOUND", "MODEL_NOT_FOUND")

test("TEST 12b: Predict /stock — generic error")
with patch("ml.ml_pipeline.predict_stock_for_api",
           side_effect=Exception("Unexpected error")):
    with patch("database.db_service.get_user_by_username", side_effect=mock_get_user):
        with app.test_client() as client:
            client2, token = _login_as(app, "admin")
            resp = client2.get("/api/predict/stock",
                headers={"Authorization": f"Bearer {token}"})
            check(resp.status_code == 500, "GET /stock (error) -> 500")
            check(resp.get_json()["code"] == "STOCK_ERROR", "STOCK_ERROR")

# ============================================================
# Summary
# ============================================================
print()
print("=" * 60)
print(f"  RESULTS: {passed} passed, {failed} failed out of {passed + failed}")
if failed:
    print("  STATUS: SOME TESTS FAILED!")
    sys.exit(1)
else:
    print("  STATUS: ALL TESTS PASSED")
print("=" * 60)
