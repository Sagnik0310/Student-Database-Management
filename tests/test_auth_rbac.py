import os
import sys
from unittest.mock import patch

# Enable isolated in-memory test store before importing app and services
os.environ["STUDENTDB_TEST_MODE"] = "1"
os.environ["SECRET_KEY"] = "test-secret-key-for-unit-and-integration-suite-2026"

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from backend.api.app import app, clear_rate_limits
from services.student_service import reset_test_students, add_student
from services.auth_service import (
    reset_test_auth,
    hash_password,
    verify_password,
    validate_password_strength,
)
from cli.menu import menu


@pytest.fixture(autouse=True)
def isolated_test_env():
    """Reset in-memory students, users, audit logs, and rate limit buckets before each test."""
    reset_test_students()
    reset_test_auth()
    clear_rate_limits()
    # Seed two sample students across CSE and ECE branches
    add_student(
        "REG2026001",
        "101",
        "Aarav Sharma",
        20,
        "CSE",
        email="aarav@university.edu",
        gpa=8.8,
        attendance_pct=91.0,
    )
    add_student(
        "REG2026002",
        "202",
        "Priya Nair",
        21,
        "ECE",
        email="priya@university.edu",
        gpa=9.2,
        attendance_pct=94.0,
    )
    yield


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def _login(client, username, password):
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    data = resp.get_json()
    return resp, data


# ==========================================
# 1. PUBLIC HEALTH & UNAUTHENTICATED ACCESS
# ==========================================
def test_public_health_endpoints_accessible_without_auth(client):
    r_home = client.get("/")
    assert r_home.status_code == 200
    assert r_home.get_json()["success"] is True

    r_health = client.get("/health")
    assert r_health.status_code == 200
    assert r_health.get_json()["status"] == "healthy"


@pytest.mark.parametrize(
    "method,path",
    [
        ("GET", "/students"),
        ("GET", "/api/v1/students"),
        ("GET", "/students/REG2026001"),
        ("POST", "/students"),
        ("PUT", "/students/REG2026001"),
        ("DELETE", "/students/REG2026001"),
        ("POST", "/students/bulk-delete"),
        ("POST", "/students/bulk-import"),
        ("GET", "/stats"),
        ("GET", "/api/v1/analytics/summary"),
        ("GET", "/api/v1/logs"),
        ("GET", "/api/v1/users"),
        ("GET", "/api/v1/auth/me"),
    ],
)
def test_unauthenticated_requests_are_rejected_with_401(client, method, path):
    resp = client.open(path, method=method, json={})
    assert resp.status_code == 401
    body = resp.get_json()
    assert body["success"] is False
    assert "Authentication required" in body["message"]


# ==========================================
# 2. PASSWORD HASHING, LOGIN, COOKIES & CSRF
# ==========================================
def test_password_hashing_and_strength_validation():
    hashed = hash_password("SecurePass123")
    assert hashed.startswith("pbkdf2:sha256:")
    assert verify_password(hashed, "SecurePass123") is True
    assert verify_password(hashed, "WrongPass123") is False
    assert validate_password_strength("short1") is not None
    assert validate_password_strength("alllettersonly") is not None
    assert validate_password_strength("ValidPass99") is None


def test_login_cookie_and_csrf_enforcement(client):
    # Invalid login
    bad_resp, _ = _login(client, "admin", "WrongPassword99")
    assert bad_resp.status_code == 401

    # Valid Admin login sets HttpOnly cookie and returns csrf_token
    resp, data = _login(client, "admin", "Admin@123")
    assert resp.status_code == 200
    assert data["user"]["role"] == "Admin"
    assert "password_hash" not in data["user"]
    csrf_token = data["csrf_token"]
    assert csrf_token

    set_cookie_header = resp.headers.get("Set-Cookie", "")
    assert "studentdb_session=" in set_cookie_header
    assert "HttpOnly" in set_cookie_header

    # State-changing POST without X-CSRF-Token must fail with 403
    no_csrf_resp = client.post(
        "/students",
        json={
            "reg_no": "REG2026003",
            "roll_no": "303",
            "name": "Rohan Verma",
            "age": 19,
            "branch": "MECH",
        },
    )
    assert no_csrf_resp.status_code == 403
    assert "CSRF" in no_csrf_resp.get_json()["message"]

    # State-changing POST with valid X-CSRF-Token succeeds with 201
    ok_resp = client.post(
        "/students",
        headers={"X-CSRF-Token": csrf_token},
        json={
            "reg_no": "REG2026003",
            "roll_no": "303",
            "name": "Rohan Verma",
            "age": 19,
            "branch": "MECH",
        },
    )
    assert ok_resp.status_code == 201


def test_login_rate_limiting_returns_429(client):
    for _ in range(10):
        r, _ = _login(client, "admin", "WrongPassword")
        assert r.status_code == 401

    # 11th request within the 60s window must be rate-limited
    blocked_resp, body = _login(client, "admin", "WrongPassword")
    assert blocked_resp.status_code == 429
    assert "Retry-After" in blocked_resp.headers
    assert "Too many requests" in body["message"]


# ==========================================
# 3. RBAC ROLE BOUNDARIES (ADMIN, FACULTY, STUDENT)
# ==========================================
def test_admin_has_full_access_to_students_analytics_users_and_logs(client):
    _, data = _login(client, "admin", "Admin@123")
    csrf = data["csrf_token"]

    # Admin sees all 2 students (CSE + ECE)
    list_resp = client.get("/students")
    assert list_resp.status_code == 200
    assert len(list_resp.get_json()) == 2

    # Admin can view analytics
    stats_resp = client.get("/stats")
    assert stats_resp.status_code == 200
    assert stats_resp.get_json()["total_students"] == 2

    # Admin can view audit logs
    logs_resp = client.get("/api/v1/logs")
    assert logs_resp.status_code == 200
    assert len(logs_resp.get_json()["logs"]) >= 1

    # Admin can create a new user
    user_resp = client.post(
        "/api/v1/users",
        headers={"X-CSRF-Token": csrf},
        json={
            "username": "student_two",
            "password": "Student2Pass",
            "role": "Student",
            "full_name": "Priya Nair",
            "linked_reg_no": "REG2026002",
        },
    )
    assert user_resp.status_code == 201

    # Admin can delete a student
    del_resp = client.delete(
        "/students/REG2026002",
        headers={"X-CSRF-Token": csrf},
    )
    assert del_resp.status_code == 200


def test_faculty_role_is_scoped_to_assigned_branch_and_cannot_create_or_delete(client):
    # faculty_cse is assigned only to ["CSE"]
    _, data = _login(client, "faculty_cse", "Faculty@123")
    csrf = data["csrf_token"]

    # GET /students returns only the CSE student (REG2026001)
    list_resp = client.get("/students")
    assert list_resp.status_code == 200
    students = list_resp.get_json()
    assert len(students) == 1
    assert students[0]["reg_no"] == "REG2026001"

    # GET /students/REG2026001 (CSE) -> 200 OK
    assert client.get("/students/REG2026001").status_code == 200

    # GET /students/REG2026002 (ECE) -> 403 Forbidden
    assert client.get("/students/REG2026002").status_code == 403

    # PUT /students/REG2026001 (CSE) -> 200 OK
    upd_ok = client.put(
        "/students/REG2026001",
        headers={"X-CSRF-Token": csrf},
        json={
            "name": "Aarav Sharma",
            "age": 20,
            "branch": "CSE",
            "gpa": 9.4,
            "attendance_pct": 96.0,
        },
    )
    assert upd_ok.status_code == 200

    # PUT /students/REG2026002 (ECE) -> 403 Forbidden
    upd_forbidden = client.put(
        "/students/REG2026002",
        headers={"X-CSRF-Token": csrf},
        json={"name": "Priya Nair", "age": 21, "branch": "ECE"},
    )
    assert upd_forbidden.status_code == 403

    # Faculty cannot create, delete, bulk-delete, or view admin audit logs
    assert (
        client.post(
            "/students",
            headers={"X-CSRF-Token": csrf},
            json={
                "reg_no": "REG2026099",
                "roll_no": "99",
                "name": "New Student",
                "age": 20,
                "branch": "CSE",
            },
        ).status_code
        == 403
    )
    assert (
        client.delete(
            "/students/REG2026001", headers={"X-CSRF-Token": csrf}
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/students/bulk-delete",
            headers={"X-CSRF-Token": csrf},
            json={"reg_nos": ["REG2026001"]},
        ).status_code
        == 403
    )
    assert client.get("/api/v1/logs").status_code == 403
    assert client.get("/api/v1/users").status_code == 403


def test_student_role_can_only_access_own_linked_record(client):
    # student_demo is linked to REG2026001
    _, data = _login(client, "student_demo", "Student@123")
    csrf = data["csrf_token"]

    # GET /students returns only REG2026001
    list_resp = client.get("/students")
    assert list_resp.status_code == 200
    students = list_resp.get_json()
    assert len(students) == 1
    assert students[0]["reg_no"] == "REG2026001"

    # GET own record -> 200 OK
    assert client.get("/students/REG2026001").status_code == 200

    # GET another student's record -> 403 Forbidden
    assert client.get("/students/REG2026002").status_code == 403

    # Student cannot create, update, delete, view analytics, or view logs
    assert (
        client.put(
            "/students/REG2026001",
            headers={"X-CSRF-Token": csrf},
            json={"name": "Tampered Name", "age": 20, "branch": "CSE"},
        ).status_code
        == 403
    )
    assert (
        client.delete(
            "/students/REG2026001", headers={"X-CSRF-Token": csrf}
        ).status_code
        == 403
    )
    assert client.get("/stats").status_code == 403
    assert client.get("/api/v1/logs").status_code == 403


# ==========================================
# 4. CLI AUTHENTICATION & RBAC SMOKE TEST
# ==========================================
def test_cli_enforces_student_role_restrictions(capsys):
    student_user = {
        "username": "student_demo",
        "role": "Student",
        "full_name": "Demo Student",
        "linked_reg_no": "REG2026001",
    }
    # Simulate choosing: 1 (Add -> denied), 3 (Search REG2026002 -> denied), 3 (Search REG2026001 -> allowed), 6 (Exit)
    inputs = iter(["1", "3", "REG2026002", "3", "REG2026001", "6"])
    with patch("builtins.input", lambda _: next(inputs)):
        menu(current_user=student_user)

    captured = capsys.readouterr().out
    assert "Access denied: Only Admin users can add students" in captured
    assert "Access denied: You can only view your own student record" in captured
    assert "Aarav Sharma" in captured

