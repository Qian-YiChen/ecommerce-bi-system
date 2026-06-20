"""
认证模块集成测试
==============
验证 苏文韬(db_service.py) + 严辰乐(auth_service/auth_routes/middleware) 的接口对接。
使用 mock 模拟数据库层，无需 MySQL。
"""
import sys
import io
import json
import inspect
from unittest.mock import patch

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from models.user import User
from auth.auth_service import (
    login, register,
    hash_password, verify_password,
    create_access_token, decode_access_token,
)

# ============================================================
# Mock DB functions — simulate db_service.py behavior
# ============================================================

def mock_get_user(username):
    """Simulate db_service.get_user_by_username"""
    if username == "admin":
        return User(
            user_id=1,
            username="admin",
            password_hash=hash_password("admin123"),
            role="admin",
            status=1,
        )
    if username == "disabled_user":
        return User(
            user_id=2,
            username="disabled_user",
            password_hash=hash_password("test123"),
            role="viewer",
            status=0,
        )
    return None


def mock_check_exists(username):
    return username == "admin"


def mock_insert_user(user):
    return 3  # mock auto-increment id


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
print("  Authentication Integration Test Suite")
print("=" * 60)

# --- Test 1: Password hash & verify ---
test("TEST 1: Password hash & verify")
h = hash_password("mypassword")
check(verify_password("mypassword", h), "correct password verified")
check(not verify_password("wrong", h), "wrong password rejected")

# --- Test 2: Successful login ---
test("TEST 2: Login success")
success, token, msg = login("admin", "admin123", mock_get_user)
check(success, f"login succeeded: {msg}")
check(token is not None and "eyJ" in token, f"JWT token generated: {token[:40]}...")

# --- Test 3: JWT decode ---
test("TEST 3: JWT decode")
payload = decode_access_token(token)
check(payload is not None, "payload decoded")
check(payload["username"] == "admin", f"username={payload['username']}")
check(payload["role"] == "admin", f"role={payload['role']}")
check(payload["sub"] == "1", f"sub(user_id)={payload['sub']}")

# --- Test 4: Wrong password ---
test("TEST 4: Wrong password")
success, token, msg = login("admin", "wrongpassword", mock_get_user)
check(not success, f"rejected: {msg}")
check(token is None, "token is None")

# --- Test 5: Non-existent user ---
test("TEST 5: Non-existent user")
success, token, msg = login("nobody", "pass", mock_get_user)
check(not success, f"rejected: {msg}")

# --- Test 6: Disabled user ---
test("TEST 6: Disabled account")
success, token, msg = login("disabled_user", "test123", mock_get_user)
check(not success and "禁用" in msg, f"rejected: {msg}")

# --- Test 7: Registration validation ---
test("TEST 7: Registration validation")
_, msg = register("ab", "123456", "viewer", mock_check_exists, mock_insert_user)[:2]
check("至少需要 3 个字符" in msg, f"short username: {msg}")

_, msg = register("newuser", "123", "viewer", mock_check_exists, mock_insert_user)[:2]
check("至少需要 6 个字符" in msg, f"short password: {msg}")

# register returns (bool, str) — 2 values
result = register("newuser", "123456", "superadmin", mock_check_exists, mock_insert_user)
check(not result[0] and "无效的角色" in result[1], f"invalid role: {result[1]}")

# --- Test 8: Duplicate username ---
test("TEST 8: Duplicate username")
success, msg = register("admin", "123456", "viewer", mock_check_exists, mock_insert_user)
check(not success and "已存在" in msg, f"duplicate rejected: {msg}")

# --- Test 9: Successful registration ---
test("TEST 9: Registration success")
success, msg = register("newuser", "newpass123", "analyst", mock_check_exists, mock_insert_user)
check(success and "ID: 3" in msg, f"registered: {msg}")

# --- Test 10: db_service interface compliance ---
test("TEST 10: db_service function signatures")
from database.db_service import (
    get_user_by_username, check_user_exists,
    insert_user, query_sales, export_report,
)

sig = inspect.signature(get_user_by_username)
check("username" in sig.parameters, f"get_user_by_username{sig}")

sig = inspect.signature(check_user_exists)
check("username" in sig.parameters, f"check_user_exists{sig}")

sig = inspect.signature(insert_user)
check("user" in sig.parameters, f"insert_user{sig}")

sig = inspect.signature(query_sales)
check(all(p in sig.parameters for p in ["start_date", "end_date"]), f"query_sales{sig}")

sig = inspect.signature(export_report)
check(all(p in sig.parameters for p in ["report_type", "params", "format"]), f"export_report{sig}")

# --- Test 11: Flask route registration ---
test("TEST 11: Flask route registration")
from app import create_app
app = create_app()

routes = {}
for r in app.url_map.iter_rules():
    methods = sorted(m for m in r.methods if m not in ("HEAD", "OPTIONS"))
    if methods:
        routes[r.rule] = methods

for path, methods in [
    ("/api/auth/login", ["POST"]),
    ("/api/auth/register", ["POST"]),
    ("/api/auth/me", ["GET"]),
    ("/api/health", ["GET"]),
]:
    found = path in routes and routes[path] == methods
    check(found, f"{path} {methods}")

# --- Test 12: End-to-end Flask test client ---
test("TEST 12: End-to-end Flask test client")

with patch("database.db_service.get_user_by_username", side_effect=mock_get_user):
    with app.test_client() as client:
        # Login success
        resp = client.post("/api/auth/login",
            data=json.dumps({"username": "admin", "password": "admin123"}),
            content_type="application/json")
        check(resp.status_code == 200, f"POST /login -> 200")
        body = resp.get_json()
        check(body["success"] is True, "login success=True")
        check(body["data"]["user"]["username"] == "admin" and body["data"]["user"]["role"] == "admin",
              f"user={body['data']['user']}")
        token = body["data"]["token"]

        # GET /me with valid token
        resp = client.get("/api/auth/me",
            headers={"Authorization": f"Bearer {token}"})
        check(resp.status_code == 200, f"GET /me -> 200")
        check(resp.get_json()["data"]["username"] == "admin", "me returns admin")

        # GET /me without token
        resp = client.get("/api/auth/me")
        check(resp.status_code == 401, f"GET /me (no token) -> 401")

        # GET /me with bad token
        resp = client.get("/api/auth/me",
            headers={"Authorization": "Bearer garbage.token.here"})
        check(resp.status_code == 401, f"GET /me (bad token) -> 401")

        # Login wrong password
        resp = client.post("/api/auth/login",
            data=json.dumps({"username": "admin", "password": "wrong"}),
            content_type="application/json")
        check(resp.status_code == 401, f"POST /login (wrong pw) -> 401")
        check(resp.get_json()["success"] is False, "login success=False")

        # Login missing fields
        resp = client.post("/api/auth/login",
            data=json.dumps({"username": ""}),
            content_type="application/json")
        check(resp.status_code == 400, f"POST /login (empty fields) -> 400")

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
