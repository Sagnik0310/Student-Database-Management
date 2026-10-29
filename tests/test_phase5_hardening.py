"""
Phase 5 Regression & Security Hardening Test Suite:
- Centralized environment & production configuration validation
- Server-side session revocation on logout (replay prevention)
- Password reset invalidation of previously issued sessions
- Zero-downtime secret key rotation (SECRET_KEY + SECRET_KEY_PREVIOUS)
- CSRF token rotation endpoint (/api/v1/auth/rotate-csrf)
- Log redaction of MongoDB URIs, passwords, cookies, CSRF tokens, and API keys
- Separated Liveness (/health, /health/live) vs. Readiness (/health/ready) probes
- Hardened HTTP security headers
"""

import os
import pytest

os.environ["STUDENTDB_TEST_MODE"] = "1"

from backend.api.app import app, create_app, clear_rate_limits
from services.rate_limit_service import (
    build_rate_limit_key,
    register_shared_test_storage,
    unregister_shared_test_storage,
    resolve_ratelimit_storage_uri,
)
from services.auth_service import (
    reset_test_auth,
    create_session_token,
    verify_session_token,
    revoke_session_token,
    is_session_revoked,
    clear_local_revocation_cache,
)
from services.config_validator import (
    validate_environment_config,
    ConfigValidationError,
)
from logs.logger import redact_sensitive_text
from services.student_service import reset_test_students
from services.academic_service import reset_test_academics


@pytest.fixture(autouse=True)
def isolated_phase5_env():
    os.environ["STUDENTDB_TEST_MODE"] = "1"
    reset_test_students()
    reset_test_auth()
    reset_test_academics()
    clear_rate_limits()
    yield


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


def _login(client, username, password):
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    return body["csrf_token"], body["session_token"]


# ==============================================================================
# 1. PRODUCTION CONFIGURATION VALIDATOR TESTS
# ==============================================================================
def test_production_config_passes_when_valid():
    valid_env = {
        "APP_ENV": "production",
        "MONGO_URI": "mongodb+srv://prod_user:StrongAtlasPass99@cluster0.example.mongodb.net/?retryWrites=true&w=majority",
        "DB_NAME": "student_db",
        "SECRET_KEY": "a9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1f0e9d8c7b6a5f4e3d2c1b0a9f8",
        "SESSION_TTL_SECONDS": "28800",
        "COOKIE_SECURE": "true",
        "COOKIE_SAMESITE": "None",
        "CORS_ORIGINS": "https://student-database-management-l3pl.onrender.com",
        "AI_ASSISTANT_PROVIDER": "deterministic",
        "ALLOW_DEFAULT_DEMO_USERS": "false",
    }
    res = validate_environment_config(env=valid_env, strict_production=True)
    assert res["valid"] is True
    assert res["production"] is True
    assert res["errors"] == []


def test_production_config_rejects_missing_or_weak_secrets():
    bad_env = {
        "APP_ENV": "production",
        "MONGO_URI": "",
        "DB_NAME": "student_db",
        "SECRET_KEY": "replace-with-a-64-char-random-cryptographic-secret",
        "COOKIE_SECURE": "false",
        "COOKIE_SAMESITE": "None",
        "CORS_ORIGINS": "*",
        "AI_ASSISTANT_PROVIDER": "gemini",
        "AI_ASSISTANT_API_KEY": "",
    }
    with pytest.raises(ConfigValidationError) as exc_info:
        validate_environment_config(env=bad_env, strict_production=True)

    errors_joined = " | ".join(exc_info.value.errors)
    assert "MONGO_URI is required in production" in errors_joined
    assert "SECRET_KEY matches a forbidden placeholder" in errors_joined
    assert "COOKIE_SECURE must be true in production" in errors_joined
    assert "Wildcard '*' in CORS_ORIGINS is forbidden" in errors_joined
    assert "AI_ASSISTANT_API_KEY is required when AI_ASSISTANT_PROVIDER='gemini'" in errors_joined


def test_production_config_allows_deterministic_ai_without_key():
    env = {
        "APP_ENV": "production",
        "MONGO_URI": "mongodb://db.internal:27017/student_db",
        "DB_NAME": "student_db",
        "SECRET_KEY": "x" * 48,
        "COOKIE_SECURE": "true",
        "COOKIE_SAMESITE": "Lax",
        "CORS_ORIGINS": "https://portal.university.edu",
        "AI_ASSISTANT_PROVIDER": "deterministic",
        "AI_ASSISTANT_API_KEY": "",
    }
    res = validate_environment_config(env=env, strict_production=True)
    assert res["valid"] is True
    assert res["ai_provider"] == "deterministic"


# ==============================================================================
# 2. SESSION LOGOUT REVOCATION & REPLAY PREVENTION
# ==============================================================================
def test_logout_revokes_session_token_preventing_replay(client):
    csrf_token, session_token = _login(client, "admin", "Admin@123")

    # Verify token works before logout via Bearer header
    me_before = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {session_token}"},
    )
    assert me_before.status_code == 200

    # Logout using the session
    logout_resp = client.post(
        "/api/v1/auth/logout",
        headers={
            "Authorization": f"Bearer {session_token}",
            "X-CSRF-Token": csrf_token,
        },
    )
    assert logout_resp.status_code == 200

    # Replaying the exact same signed token after logout must be rejected (401)
    me_after = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {session_token}"},
    )
    assert me_after.status_code == 401
    assert verify_session_token(session_token) is None


def test_cookie_logout_enforces_csrf_header(client):
    csrf_token, _ = _login(client, "admin", "Admin@123")

    # Cookie-authenticated logout without X-CSRF-Token is rejected with 403
    no_csrf_logout = client.post("/api/v1/auth/logout")
    assert no_csrf_logout.status_code == 403

    # Cookie-authenticated logout with valid X-CSRF-Token succeeds
    ok_logout = client.post(
        "/api/v1/auth/logout",
        headers={"X-CSRF-Token": csrf_token},
    )
    assert ok_logout.status_code == 200
    assert client.get("/api/v1/auth/me").status_code == 401


def test_multi_worker_mongodb_session_revocation_and_fail_closed_behavior(monkeypatch):
    import services.auth_service as auth_mod

    token, _ = create_session_token({"username": "admin", "role": "Admin"})
    assert verify_session_token(token) is not None

    # Shared fake MongoDB store representing two separate Gunicorn worker processes
    shared_revoked_docs = {}
    shared_user_docs = {
        "admin": {
            "username": "admin",
            "role": "Admin",
            "is_active": True,
            "tokens_valid_after": None,
        }
    }

    class _FakeRevokedCol:
        def update_one(self, flt, upd, upsert=False):
            jti = flt["jti"]
            shared_revoked_docs[jti] = dict(upd.get("$set", {}))

        def find_one(self, flt):
            return shared_revoked_docs.get(flt.get("jti"))

    class _FakeUsersCol:
        def find_one(self, flt, proj=None):
            return shared_user_docs.get(flt.get("username"))

    fake_db = {
        "revoked_sessions": _FakeRevokedCol(),
        "users": _FakeUsersCol(),
    }

    monkeypatch.setenv("STUDENTDB_TEST_MODE", "0")
    monkeypatch.setattr(auth_mod, "get_connection", lambda: fake_db)

    # Worker 1 verifies token is valid before logout
    clear_local_revocation_cache()
    assert verify_session_token(token) is not None

    # Worker 1 revokes token -> persisted in shared MongoDB revoked_sessions
    assert revoke_session_token(token) is True
    assert len(shared_revoked_docs) == 1

    # Simulate Worker 2 (fresh in-memory cache, reads only from MongoDB)
    clear_local_revocation_cache()
    assert verify_session_token(token) is None

    # Issue a second token and simulate password reset on Worker 1 updating MongoDB users.tokens_valid_after
    token_2, _ = create_session_token({"username": "admin", "role": "Admin"})
    clear_local_revocation_cache()
    assert verify_session_token(token_2) is not None

    import time

    shared_user_docs["admin"]["tokens_valid_after"] = time.time_ns()
    clear_local_revocation_cache()
    # Worker 2 rejects token_2 via MongoDB tokens_valid_after
    assert verify_session_token(token_2) is None

    # Issue token_3 after password reset -> valid on Worker 2
    token_3, _ = create_session_token({"username": "admin", "role": "Admin"})
    clear_local_revocation_cache()
    assert verify_session_token(token_3) is not None

    # Simulate MongoDB outage (get_connection returns None) -> must FAIL CLOSED
    clear_local_revocation_cache()
    monkeypatch.setattr(auth_mod, "get_connection", lambda: None)
    assert verify_session_token(token_3) is None
    assert revoke_session_token(token_3) is False


def test_expired_and_tampered_session_tokens_are_rejected():
    # Expired token
    expired_token, _ = create_session_token(
        {"username": "admin", "role": "Admin"}, ttl_seconds=-10
    )
    assert verify_session_token(expired_token) is None

    # Tampered signature
    valid_token, _ = create_session_token({"username": "admin", "role": "Admin"})
    b64_part, _ = valid_token.rsplit(".", 1)
    assert verify_session_token(f"{b64_part}.0000000000000000") is None

    # Missing jti fails closed
    assert is_session_revoked({"username": "admin", "role": "Admin"}) is True



# ==============================================================================
# 3. PASSWORD RESET INVALIDATES ACTIVE SESSIONS
# ==============================================================================
def test_password_reset_invalidates_existing_sessions(client):
    csrf_token, old_session_token = _login(client, "faculty_cse", "Faculty@123")

    # Reset password while authenticated
    reset_resp = client.post(
        "/api/v1/auth/reset-password",
        headers={
            "Authorization": f"Bearer {old_session_token}",
            "X-CSRF-Token": csrf_token,
        },
        json={
            "current_password": "Faculty@123",
            "new_password": "NewStrongFaculty@456",
        },
    )
    assert reset_resp.status_code == 200

    # Old session token issued before password reset must now be rejected
    replay_resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {old_session_token}"},
    )
    assert replay_resp.status_code == 401

    # Logging in with the new password issues a fresh valid session
    _, new_session_token = _login(client, "faculty_cse", "NewStrongFaculty@456")
    valid_resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {new_session_token}"},
    )
    assert valid_resp.status_code == 200


# ==============================================================================
# 4. ZERO-DOWNTIME SECRET KEY ROTATION & CSRF ROTATION
# ==============================================================================
def test_secret_key_rotation_with_previous_key(monkeypatch):
    old_key = "old-production-secret-key-at-least-32-bytes-long-1111"
    new_key = "new-production-secret-key-at-least-32-bytes-long-2222"

    monkeypatch.setenv("SECRET_KEY", old_key)
    monkeypatch.delenv("SECRET_KEY_PREVIOUS", raising=False)

    token, _ = create_session_token({"username": "admin", "role": "Admin"})
    assert verify_session_token(token) is not None

    # Rotate SECRET_KEY to new_key while keeping old_key in SECRET_KEY_PREVIOUS
    monkeypatch.setenv("SECRET_KEY", new_key)
    monkeypatch.setenv("SECRET_KEY_PREVIOUS", old_key)

    payload = verify_session_token(token)
    assert payload is not None
    assert payload["username"] == "admin"

    # Once SECRET_KEY_PREVIOUS is retired, the old token is rejected
    monkeypatch.delenv("SECRET_KEY_PREVIOUS", raising=False)
    assert verify_session_token(token) is None


def test_csrf_rotation_endpoint_revokes_previous_token(client):
    csrf_1, token_1 = _login(client, "admin", "Admin@123")

    rot_resp = client.post(
        "/api/v1/auth/rotate-csrf",
        headers={
            "Authorization": f"Bearer {token_1}",
            "X-CSRF-Token": csrf_1,
        },
    )
    assert rot_resp.status_code == 200
    body = rot_resp.get_json()
    assert body["csrf_token"] != csrf_1
    assert body["session_token"] != token_1

    # Old token is revoked
    assert verify_session_token(token_1) is None
    # New token is active
    assert verify_session_token(body["session_token"]) is not None


# ==============================================================================
# 5. SENSITIVE LOG REDACTION
# ==============================================================================
def test_log_redaction_scrubs_uris_passwords_tokens_and_api_keys():
    # Synthetic, non-functional key assembled at runtime so repository secret
    # scanners (e.g. GitHub push protection) do not flag this test fixture.
    fake_google_key = "AIza" + "SyD-1234567890abcdefghijklmnopqrstuv"
    raw_log = (
        "Connecting to mongodb+srv://dbadmin:MySuperSecretPass99@cluster0.abc.mongodb.net/student_db "
        "with header Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.payload.sig "
        "cookie studentdb_session=abc123secretcookie "
        'payload {"password": "PlaintextPassword123", "csrf_token": "csrf_secret_999"} '
        f"AI key {fake_google_key}"
    )
    scrubbed = redact_sensitive_text(raw_log)
    assert "MySuperSecretPass99" not in scrubbed
    assert "eyJhbGciOiJIUzI1NiJ9.payload.sig" not in scrubbed
    assert "abc123secretcookie" not in scrubbed
    assert "PlaintextPassword123" not in scrubbed
    assert "csrf_secret_999" not in scrubbed
    assert fake_google_key not in scrubbed
    assert "[REDACTED]" in scrubbed


# ==============================================================================
# 6. LIVENESS vs. READINESS HEALTH PROBES & SECURITY HEADERS
# ==============================================================================
def test_liveness_and_readiness_endpoints_and_security_headers(client, monkeypatch):
    live_resp = client.get("/health/live")
    assert live_resp.status_code == 200
    live_data = live_resp.get_json()
    assert live_data["status"] == "healthy"
    assert live_data["probe"] == "liveness"
    assert live_resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert live_resp.headers.get("X-Frame-Options") == "DENY"
    assert "strict-origin-when-cross-origin" in live_resp.headers.get("Referrer-Policy", "")

    ready_resp = client.get("/api/v1/health/ready")
    assert ready_resp.status_code == 200
    ready_data = ready_resp.get_json()
    assert ready_data["status"] == "ready"
    assert ready_data["probe"] == "readiness"
    assert ready_resp.headers.get("Cache-Control") == "no-store"

    # Simulate database unavailability on readiness probe
    import backend.api.app as app_module

    monkeypatch.setattr(
        app_module,
        "check_db_readiness",
        lambda: {"ready": False, "status": "unavailable", "database": "disconnected"},
    )
    unready_resp = client.get("/health/ready")
    assert unready_resp.status_code == 503
    unready_data = unready_resp.get_json()
    assert unready_data["success"] is False
    assert unready_data["status"] == "unavailable"


def test_runtime_operations_never_log_credentials_tokens_or_student_record_dumps(
    client, caplog
):
    import logging
    from logs.logger import logger as app_logger, RedactingFilter

    caplog.set_level(logging.INFO)
    caplog.handler.addFilter(RedactingFilter())
    app_logger.addHandler(caplog.handler)
    try:
        csrf_token, session_token = _login(client, "admin", "Admin@123")

        create_resp = client.post(
            "/students",
            headers={
                "Authorization": f"Bearer {session_token}",
                "X-CSRF-Token": csrf_token,
            },
            json={
                "reg_no": "REG2026999",
                "roll_no": "999",
                "name": "Confidential Student Name",
                "age": 21,
                "branch": "CSE",
                "email": "confidential.student@univ.edu",
                "phone": "9876543210",
            },
        )
        assert create_resp.status_code in (200, 201)

        client.get(
            "/students",
            headers={"Authorization": f"Bearer {session_token}"},
        )
        client.post(
            "/api/v1/auth/logout",
            headers={
                "Authorization": f"Bearer {session_token}",
                "X-CSRF-Token": csrf_token,
            },
        )

        combined_logs = "\n".join(record.getMessage() for record in caplog.records)
        assert len(caplog.records) > 0
        # Must never contain passwords, session tokens, CSRF tokens, or student PII dumps
        assert "Admin@123" not in combined_logs
        assert session_token not in combined_logs
        assert csrf_token not in combined_logs
        assert "Confidential Student Name" not in combined_logs
        assert "confidential.student@univ.edu" not in combined_logs
        assert "9876543210" not in combined_logs
    finally:
        app_logger.removeHandler(caplog.handler)


# ==============================================================================
# 7. DISTRIBUTED SHARED RATE LIMITING & FAIL-CLOSED POLICY
# ==============================================================================
def test_two_independent_create_app_instances_share_rate_limits(monkeypatch):
    """
    Prove that two independently initialized Flask application instances
    (representing two separate Gunicorn workers) share rate-limit counters
    through the configured shared backend rather than maintaining separate
    per-worker limits.
    """
    shared_uri = "redis://shared-test-cluster.internal:6379/0"
    register_shared_test_storage(shared_uri)
    monkeypatch.setenv("RATELIMIT_STORAGE_URI", shared_uri)

    try:
        worker_1 = create_app(validate_config=False)
        worker_2 = create_app(validate_config=False)
        worker_1.config["TESTING"] = True
        worker_2.config["TESTING"] = True

        # Ensure the two app instances and their rate-limiter extensions are distinct objects
        assert worker_1 is not worker_2
        assert (
            worker_1.extensions["studentdb_rate_limiter"]
            is not worker_2.extensions["studentdb_rate_limiter"]
        )

        client_1 = worker_1.test_client()
        client_2 = worker_2.test_client()
        headers = {"X-Forwarded-For": "203.0.113.77"}

        # Send 5 login requests to Worker 1 (limit is 10 per 60s on scope 'auth_login')
        for i in range(5):
            r1 = client_1.post(
                "/api/v1/auth/login",
                json={"username": "admin", "password": "wrong-password"},
                headers=headers,
            )
            assert r1.status_code == 401
            assert r1.headers.get("X-RateLimit-Limit") == "10"
            assert int(r1.headers.get("X-RateLimit-Remaining")) == 9 - i

        # Send 5 login requests to Worker 2 — continues decrementing the shared counter (4 -> 0)
        for i in range(5):
            r2 = client_2.post(
                "/api/v1/auth/login",
                json={"username": "admin", "password": "wrong-password"},
                headers=headers,
            )
            assert r2.status_code == 401
            assert r2.headers.get("X-RateLimit-Limit") == "10"
            assert int(r2.headers.get("X-RateLimit-Remaining")) == 4 - i

        # 11th request on Worker 1 must be rate-limited (HTTP 429)
        blocked_1 = client_1.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "Admin@123"},
            headers=headers,
        )
        assert blocked_1.status_code == 429
        assert int(blocked_1.headers.get("Retry-After", "0")) >= 1
        assert blocked_1.headers.get("X-RateLimit-Remaining") == "0"
        body_1 = blocked_1.get_json()
        assert body_1["success"] is False
        assert "Too many requests" in body_1["error"]

        # 12th request on Worker 2 must ALSO be rate-limited (HTTP 429)
        blocked_2 = client_2.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "Admin@123"},
            headers=headers,
        )
        assert blocked_2.status_code == 429
        assert int(blocked_2.headers.get("Retry-After", "0")) >= 1
    finally:
        unregister_shared_test_storage(shared_uri)


def test_rate_limiter_fail_closed_policy_when_shared_backend_unavailable(monkeypatch):
    """
    Prove that when the shared rate-limit storage backend is unreachable or raises
    an error, protected endpoints reject requests with HTTP 503 Service Unavailable
    (fail-closed policy) and never fall back to unrestricted requests or per-worker memory.
    """
    from limits.storage import MemoryStorage

    class _BrokenSharedStorage(MemoryStorage):
        def acquire_entry(self, *args, **kwargs):
            raise ConnectionError("Simulated Redis cluster connection failure")

        def get(self, *args, **kwargs):
            raise ConnectionError("Simulated Redis cluster connection failure")

    broken_uri = "redis://broken-cluster.internal:6379/0"
    register_shared_test_storage(broken_uri, _BrokenSharedStorage())
    monkeypatch.setenv("RATELIMIT_STORAGE_URI", broken_uri)
    monkeypatch.setenv("RATELIMIT_FAIL_CLOSED", "true")

    try:
        worker_1 = create_app(validate_config=False)
        worker_2 = create_app(validate_config=False)
        worker_1.config["TESTING"] = True
        worker_2.config["TESTING"] = True

        resp_1 = worker_1.test_client().post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "Admin@123"},
        )
        assert resp_1.status_code == 503
        data_1 = resp_1.get_json()
        assert data_1["success"] is False
        assert "fail-closed" in data_1["error"].lower()

        resp_2 = worker_2.test_client().post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "Admin@123"},
        )
        assert resp_2.status_code == 503

        # Public liveness probe remains accessible for container orchestrators
        live = worker_1.test_client().get("/health/live")
        assert live.status_code == 200
    finally:
        unregister_shared_test_storage(broken_uri)


def test_production_config_and_rate_limiter_reject_memory_backend():
    bad_prod_env = {
        "APP_ENV": "production",
        "MONGO_URI": "mongodb+srv://prod_user:StrongAtlasPass99@cluster0.example.mongodb.net/?retryWrites=true&w=majority",
        "DB_NAME": "student_db",
        "SECRET_KEY": "a9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1f0e9d8c7b6a5f4e3d2c1b0a9f8",
        "COOKIE_SECURE": "true",
        "COOKIE_SAMESITE": "None",
        "CORS_ORIGINS": "https://student-database-management-l3pl.onrender.com",
        "AI_ASSISTANT_PROVIDER": "deterministic",
        "RATELIMIT_STORAGE_URI": "memory://",
    }
    with pytest.raises(ConfigValidationError) as exc_info:
        validate_environment_config(env=bad_prod_env, strict_production=True)
    assert "RATELIMIT_STORAGE_URI cannot use process-local 'memory://' in production" in " | ".join(
        exc_info.value.errors
    )

    with pytest.raises(RuntimeError, match="forbidden in production"):
        resolve_ratelimit_storage_uri(env=bad_prod_env, strict_production=True)


def test_rate_limit_keys_and_logs_contain_no_raw_ip_passwords_or_pii():
    raw_ip = "198.51.100.42"
    rl_key, extracted_ip = build_rate_limit_key("auth_login", client_ip=raw_ip)
    assert extracted_ip == raw_ip
    assert rl_key.startswith("rl:auth_login:")
    assert raw_ip not in rl_key

    redis_log = (
        "Failed connecting to RATELIMIT_STORAGE_URI=redis://default:MyRedisSecretPass99@redis.internal:6379/0 "
        "and rediss://tlsuser:MyValkeySecret88@valkey.cloud:6380/0"
    )
    scrubbed = redact_sensitive_text(redis_log)
    assert "MyRedisSecretPass99" not in scrubbed
    assert "MyValkeySecret88" not in scrubbed
    assert "[REDACTED]" in scrubbed




# ==============================================================================
# 8. DEPLOYMENT-READINESS REGRESSIONS (bootstrap credentials, CORS, proxy IPs)
# ==============================================================================
_PROD_BASE_ENV = {
    "APP_ENV": "production",
    "MONGO_URI": "mongodb+srv://prod_user:StrongAtlasPass99@cluster0.example.mongodb.net/?retryWrites=true&w=majority",
    "DB_NAME": "student_db",
    "SECRET_KEY": "a9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1f0e9d8c7b6a5f4e3d2c1b0a9f8",
    "COOKIE_SECURE": "true",
    "COOKIE_SAMESITE": "None",
    "CORS_ORIGINS": "https://student-portal.example.onrender.com",
    "AI_ASSISTANT_PROVIDER": "deterministic",
}


def _bootstrap_under_env(monkeypatch, overrides):
    """Re-run account bootstrap with production env (no MongoDB) and return usernames."""
    import services.auth_service as auth_mod

    monkeypatch.setenv("STUDENTDB_TEST_MODE", "0")
    monkeypatch.setenv("APP_ENV", "production")
    for key in (
        "ADMIN_PASSWORD", "DEFAULT_ADMIN_PASSWORD",
        "FACULTY_PASSWORD", "DEFAULT_FACULTY_PASSWORD",
        "STUDENT_PASSWORD", "DEFAULT_STUDENT_PASSWORD",
        "ALLOW_DEFAULT_DEMO_USERS",
    ):
        monkeypatch.delenv(key, raising=False)
    for key, value in overrides.items():
        monkeypatch.setenv(key, value)

    auth_mod._memory_users.clear()
    auth_mod._bootstrapped = False
    auth_mod._ensure_bootstrap_users(None)
    return dict(auth_mod._memory_users)


def test_production_bootstrap_never_creates_demo_password_accounts(monkeypatch):
    import services.auth_service as auth_mod

    try:
        # 1. No ADMIN_PASSWORD in production -> no accounts with hard-coded demo passwords
        users = _bootstrap_under_env(monkeypatch, {})
        assert users == {}

        # 2. Known demo password explicitly configured -> still rejected
        users = _bootstrap_under_env(monkeypatch, {"ADMIN_PASSWORD": "Admin@123"})
        assert users == {}

        # 3. Strong ADMIN_PASSWORD -> only Admin is created; demo Faculty/Student are not
        strong = "Rotated-Admin-Passphrase-2026"
        users = _bootstrap_under_env(monkeypatch, {"ADMIN_PASSWORD": strong})
        assert set(users) == {"admin"}
        assert auth_mod.verify_password(users["admin"]["password_hash"], strong)
        assert not auth_mod.verify_password(users["admin"]["password_hash"], "Admin@123")

        # 4. Demo accounts require explicit opt-in AND strong passwords
        users = _bootstrap_under_env(
            monkeypatch,
            {
                "ADMIN_PASSWORD": strong,
                "ALLOW_DEFAULT_DEMO_USERS": "true",
                "FACULTY_PASSWORD": "Faculty@123",
                "STUDENT_PASSWORD": "Staging-Student-Passphrase-77",
            },
        )
        assert set(users) == {"admin", "student_demo"}
    finally:
        monkeypatch.undo()
        os.environ["STUDENTDB_TEST_MODE"] = "1"
        reset_test_auth()

    # Development/test mode keeps documented demo accounts for local use
    assert set(auth_mod._memory_users) == {"admin", "faculty_cse", "student_demo"}


def test_production_validator_rejects_weak_bootstrap_passwords_and_insecure_origins():
    # Weak / demo bootstrap passwords (documented names, not just DEFAULT_* aliases)
    env = dict(_PROD_BASE_ENV, ADMIN_PASSWORD="Admin@123", FACULTY_PASSWORD="Short1")
    with pytest.raises(ConfigValidationError) as exc_info:
        validate_environment_config(env=env, strict_production=True)
    joined = " | ".join(exc_info.value.errors)
    assert "ADMIN_PASSWORD uses a known default demo password" in joined
    assert "FACULTY_PASSWORD must be at least 12 characters" in joined
    assert "Admin@123" not in str(exc_info.value)  # never echo secret values

    # Plain-HTTP and trailing-slash origins are rejected in production
    env = dict(
        _PROD_BASE_ENV,
        CORS_ORIGINS="http://localhost:3000,https://student-portal.example.onrender.com/",
    )
    with pytest.raises(ConfigValidationError) as exc_info:
        validate_environment_config(env=env, strict_production=True)
    joined = " | ".join(exc_info.value.errors)
    assert "must use https:// in production" in joined
    assert "must not include a trailing slash" in joined

    # Missing ADMIN_PASSWORD is a warning (an Admin may already exist), not an error
    res = validate_environment_config(env=dict(_PROD_BASE_ENV), strict_production=True)
    assert res["valid"] is True
    assert any("ADMIN_PASSWORD is not set" in w for w in res["warnings"])


def test_spoofed_x_forwarded_for_cannot_bypass_rate_limits():
    """
    Behind Render's proxy the trusted hop appends the real client IP as the
    right-most X-Forwarded-For entry. Rotating the client-controlled left-most
    value must NOT create fresh rate-limit buckets.
    """
    worker = create_app(validate_config=False)
    worker.config["TESTING"] = True
    client = worker.test_client()
    real_client_ip = "198.51.100.9"

    statuses = []
    for i in range(11):
        resp = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "wrong-password"},
            headers={"X-Forwarded-For": f"10.0.0.{i}, {real_client_ip}"},
        )
        statuses.append(resp.status_code)

    assert statuses[:10] == [401] * 10
    assert statuses[10] == 429
