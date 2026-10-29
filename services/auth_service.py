import os
import re
import hmac
import json
import time
import base64
import hashlib
import secrets
from datetime import datetime, timezone
from database.db_connection import get_connection
from models.user import User
from logs.logger import logger

# Ephemeral fallback secret if SECRET_KEY is not configured in environment
_DEFAULT_RUNTIME_SECRET = secrets.token_hex(32)
PBKDF2_ITERATIONS = 260000

# In-memory session revocation & password-reset invalidation stores
_revoked_sessions = {}  # jti -> exp timestamp
_user_tokens_valid_after = {}  # username -> unix timestamp


def _get_secret_key():
    env_secret = (
        os.getenv("SECRET_KEY", "").strip()
        or os.getenv("JWT_SECRET_KEY", "").strip()
    )
    return (env_secret or _DEFAULT_RUNTIME_SECRET).encode("utf-8")


def _get_verification_secret_keys():
    """Return active signing key plus optional previous key for zero-downtime key rotation."""
    keys = [_get_secret_key()]
    prev_secret = os.getenv("SECRET_KEY_PREVIOUS", "").strip()
    if prev_secret:
        prev_bytes = prev_secret.encode("utf-8")
        if prev_bytes not in keys:
            keys.append(prev_bytes)
    return keys


# ==========================================
# PASSWORD HASHING & VALIDATION
# ==========================================
def hash_password(plain_password):
    """Hash a password using PBKDF2-HMAC-SHA256 with a cryptographic random salt."""
    password_bytes = str(plain_password or "").encode("utf-8")
    salt = secrets.token_hex(16)
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password_bytes,
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS,
    ).hex()
    return f"pbkdf2:sha256:{PBKDF2_ITERATIONS}${salt}${derived}"


def verify_password(stored_hash, plain_password):
    """Verify a plaintext password against a stored PBKDF2-HMAC-SHA256 hash in constant time."""
    if not stored_hash or not plain_password:
        return False
    try:
        parts = str(stored_hash).split("$")
        if len(parts) != 3:
            return False
        header, salt, expected_hex = parts
        header_parts = header.split(":")
        iterations = int(header_parts[2]) if len(header_parts) >= 3 else PBKDF2_ITERATIONS
        candidate_hex = hashlib.pbkdf2_hmac(
            "sha256",
            str(plain_password).encode("utf-8"),
            salt.encode("utf-8"),
            iterations,
        ).hex()
        return hmac.compare_digest(expected_hex, candidate_hex)
    except Exception:
        return False


def validate_password_strength(password):
    """Validate password complexity requirements."""
    pwd = str(password or "")
    if len(pwd) < 8:
        return "Password must be at least 8 characters long"
    if not re.search(r"[A-Za-z]", pwd) or not re.search(r"[0-9]", pwd):
        return "Password must contain at least one letter and one number"
    return None


# ==========================================
# SIGNED SESSION, REVOCATION & CSRF TOKENS
# ==========================================
def _get_default_session_ttl():
    try:
        val = int(os.getenv("SESSION_TTL_SECONDS", "28800"))
        return max(60, min(val, 604800))
    except ValueError:
        return 28800


def create_session_token(user_dict, ttl_seconds=None):
    """Create an HMAC-SHA256 signed, time-limited session token with unique jti and embedded CSRF token."""
    now = int(time.time())
    now_ns = time.time_ns()
    effective_ttl = (
        int(ttl_seconds) if ttl_seconds is not None else _get_default_session_ttl()
    )
    csrf_token = secrets.token_urlsafe(24)
    jti = secrets.token_hex(16)
    payload = {
        "jti": jti,
        "username": user_dict["username"],
        "role": user_dict["role"],
        "full_name": user_dict.get("full_name", user_dict["username"]),
        "assigned_branches": user_dict.get("assigned_branches", []),
        "assigned_reg_nos": user_dict.get("assigned_reg_nos", []),
        "linked_reg_no": user_dict.get("linked_reg_no", ""),
        "csrf_token": csrf_token,
        "iat": now,
        "iat_ns": now_ns,
        "exp": now + effective_ttl,
    }
    payload_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    b64_payload = base64.urlsafe_b64encode(payload_bytes).decode("ascii").rstrip("=")
    signature = hmac.new(
        _get_secret_key(),
        b64_payload.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()
    return f"{b64_payload}.{signature}", csrf_token


def _prune_expired_revocations(now=None):
    current = int(now if now is not None else time.time())
    expired_jtis = [
        jti for jti, exp in list(_revoked_sessions.items()) if int(exp or 0) < current
    ]
    for jti in expired_jtis:
        _revoked_sessions.pop(jti, None)


def clear_local_revocation_cache():
    """Clear process-local revocation and password-reset caches (simulates a separate Gunicorn worker)."""
    _revoked_sessions.clear()
    _user_tokens_valid_after.clear()


def is_session_revoked(payload):
    """
    Check whether a session payload has been revoked by logout or password reset.
    Fails closed (returns True) if payload metadata is missing or if revocation
    status cannot be verified against MongoDB in non-test mode.
    """
    if not payload or not isinstance(payload, dict):
        return True

    now = int(time.time())
    _prune_expired_revocations(now)

    jti = str(payload.get("jti") or "").strip()
    username = str(payload.get("username") or "").strip()
    if not jti or not username:
        return True

    iat_ns = int(payload.get("iat_ns") or (int(payload.get("iat") or 0) * 1_000_000_000))

    if jti in _revoked_sessions:
        return True

    # Check if user's password was reset after token issuance
    valid_after = _user_tokens_valid_after.get(username)
    if valid_after is not None and iat_ns <= int(valid_after):
        return True

    if os.environ.get("STUDENTDB_TEST_MODE") != "1":
        db = get_connection()
        if db is None:
            logger.error(
                f"Cannot verify session revocation for '{username}': database unavailable (failing closed)."
            )
            return True
        try:
            if db["revoked_sessions"].find_one({"jti": jti}):
                _revoked_sessions[jti] = int(payload.get("exp") or (now + 3600))
                return True
            u_doc = db["users"].find_one(
                {"username": username}, {"tokens_valid_after": 1, "is_active": 1}
            )
            if not u_doc or not u_doc.get("is_active", True):
                return True
            db_valid_after = u_doc.get("tokens_valid_after")
            if db_valid_after is not None and iat_ns <= int(db_valid_after):
                _user_tokens_valid_after[username] = int(db_valid_after)
                return True
        except Exception as exc:
            logger.error(
                f"Session revocation query failed for '{username}', failing closed: {exc}"
            )
            return True

    return False


def revoke_session_token(token_or_payload):
    """
    Revoke a session token (by raw token string or decoded payload dict) so it
    can no longer be used across any worker. Returns False if revocation cannot
    be persisted in non-test mode.
    """
    payload = None
    if isinstance(token_or_payload, dict):
        payload = token_or_payload
    elif isinstance(token_or_payload, str) and "." in token_or_payload:
        payload = verify_session_token(token_or_payload, check_revocation=False)

    if not payload or not isinstance(payload, dict):
        return False

    jti = str(payload.get("jti") or "").strip()
    exp = int(payload.get("exp") or (int(time.time()) + 28800))
    username = str(payload.get("username") or "").strip()

    if not jti:
        return False

    _revoked_sessions[jti] = exp

    if os.environ.get("STUDENTDB_TEST_MODE") != "1":
        db = get_connection()
        if db is None:
            logger.error(
                f"Could not persist session revocation for '{username}': database unavailable."
            )
            return False
        try:
            db["revoked_sessions"].update_one(
                {"jti": jti},
                {
                    "$set": {
                        "jti": jti,
                        "username": username,
                        "exp": exp,
                        "expires_at": datetime.fromtimestamp(exp, tz=timezone.utc),
                        "revoked_at": datetime.now(timezone.utc).isoformat(),
                    }
                },
                upsert=True,
            )
        except Exception as exc:
            logger.error(f"Could not persist session revocation for {username}: {exc}")
            return False

    return True


def rotate_csrf_token(session_payload):
    """Rotate the session and CSRF token, revoking the old session JTI."""
    if not session_payload or not isinstance(session_payload, dict):
        return None, None
    if not revoke_session_token(session_payload):
        return None, None
    remaining_ttl = max(
        60, int(session_payload.get("exp", int(time.time()) + 3600)) - int(time.time())
    )
    return create_session_token(session_payload, ttl_seconds=remaining_ttl)


def verify_session_token(token, check_revocation=True):
    """Verify an HMAC-SHA256 signed session token (supporting key rotation) and check expiration and revocation."""
    if not token or not isinstance(token, str) or "." not in token:
        return None
    try:
        b64_payload, provided_sig = token.rsplit(".", 1)
        sig_valid = False
        for key in _get_verification_secret_keys():
            expected_sig = hmac.new(
                key,
                b64_payload.encode("ascii"),
                hashlib.sha256,
            ).hexdigest()
            if hmac.compare_digest(expected_sig, provided_sig):
                sig_valid = True
                break

        if not sig_valid:
            return None

        padding = "=" * (-len(b64_payload) % 4)
        payload_json = base64.urlsafe_b64decode(b64_payload + padding).decode("utf-8")
        payload = json.loads(payload_json)

        if int(payload.get("exp", 0)) < int(time.time()):
            return None

        if check_revocation and is_session_revoked(payload):
            return None

        return payload
    except Exception:
        return None


def verify_csrf_token(session_payload, provided_csrf):
    """Verify CSRF header token matches the session's bound CSRF token."""
    if not session_payload or not provided_csrf:
        return False
    expected = str(session_payload.get("csrf_token") or "")
    if not expected:
        return False
    return hmac.compare_digest(expected, str(provided_csrf))


# ==========================================
# USER & AUDIT STORAGE LAYER
# ==========================================
_memory_users = {}
_memory_audit_logs = []
_bootstrapped = False


def reset_test_auth():
    """Reset the in-memory user, revocation, and audit stores for isolated unit tests."""
    global _bootstrapped
    _memory_users.clear()
    _memory_audit_logs.clear()
    _revoked_sessions.clear()
    _user_tokens_valid_after.clear()
    _bootstrapped = False
    _ensure_bootstrap_users(None)


def _get_db_collections():
    if os.environ.get("STUDENTDB_TEST_MODE") == "1":
        return None, None
    db = get_connection()
    if db is None:
        return None, None
    try:
        users_col = db["users"]
        audit_col = db["audit_logs"]
        users_col.create_index("username", unique=True, background=True)
        return users_col, audit_col
    except Exception:
        return None, None


_KNOWN_DEMO_PASSWORDS = {"Admin@123", "Faculty@123", "Student@123"}


def _resolve_bootstrap_password(primary_env, legacy_env, demo_default, production):
    """
    Resolve a bootstrap account password.

    Development/test: falls back to the documented demo password.
    Production: returns None (skip account creation) unless an explicit, non-demo,
    policy-compliant password is configured. Secret values are never logged.
    """
    explicit = (os.getenv(primary_env) or os.getenv(legacy_env) or "").strip()
    if not production:
        return explicit or demo_default
    if not explicit:
        return None
    if explicit in _KNOWN_DEMO_PASSWORDS or validate_password_strength(explicit):
        return None
    return explicit


def _ensure_bootstrap_users(users_col=None):
    """
    Ensure initial Admin, Faculty, and Student accounts exist so the system can be accessed.

    In production mode, hard-coded demo passwords are never used:
    - The Admin account is created only when ADMIN_PASSWORD is explicitly set to a
      non-demo, policy-compliant value.
    - Faculty/Student demo accounts are created only when ALLOW_DEFAULT_DEMO_USERS=true
      and their passwords are explicitly set to non-demo, policy-compliant values.
    Existing accounts in MongoDB are never modified.
    """
    global _bootstrapped
    if _bootstrapped:
        return

    from services.config_validator import is_production_mode

    production = is_production_mode()
    allow_demo_users = str(
        os.getenv("ALLOW_DEFAULT_DEMO_USERS", "false" if production else "true")
    ).strip().lower() in {"1", "true", "yes", "on"}

    admin_username = (
        os.getenv("ADMIN_USERNAME") or os.getenv("DEFAULT_ADMIN_USERNAME") or "admin"
    ).strip()
    admin_password = _resolve_bootstrap_password(
        "ADMIN_PASSWORD", "DEFAULT_ADMIN_PASSWORD", "Admin@123", production
    )
    faculty_username = (
        os.getenv("FACULTY_USERNAME")
        or os.getenv("DEFAULT_FACULTY_USERNAME")
        or "faculty_cse"
    ).strip()
    faculty_password = _resolve_bootstrap_password(
        "FACULTY_PASSWORD", "DEFAULT_FACULTY_PASSWORD", "Faculty@123", production
    )
    student_username = (
        os.getenv("STUDENT_USERNAME")
        or os.getenv("DEFAULT_STUDENT_USERNAME")
        or "student_demo"
    ).strip()
    student_password = _resolve_bootstrap_password(
        "STUDENT_PASSWORD", "DEFAULT_STUDENT_PASSWORD", "Student@123", production
    )
    student_reg_no = os.getenv("STUDENT_LINKED_REG_NO", "REG2026001").strip()

    if production and not allow_demo_users:
        faculty_password = None
        student_password = None

    if production and admin_password is None:
        logger.warning(
            "Bootstrap: Admin account not auto-created in production because "
            "ADMIN_PASSWORD is unset, a known demo value, or fails the password policy."
        )

    defaults = []
    if admin_password is not None:
        defaults.append(User(
            username=admin_username,
            password_hash=hash_password(admin_password),
            role="Admin",
            full_name="System Administrator",
            email="admin@studentdb.edu",
            assigned_branches=["*"],
        ))
    if faculty_password is not None:
        defaults.append(User(
            username=faculty_username,
            password_hash=hash_password(faculty_password),
            role="Faculty",
            full_name="Prof. CSE Coordinator",
            email="faculty.cse@studentdb.edu",
            assigned_branches=["CSE"],
        ))
    if student_password is not None:
        defaults.append(User(
            username=student_username,
            password_hash=hash_password(student_password),
            role="Student",
            full_name="Demo Student",
            email="student@studentdb.edu",
            linked_reg_no=student_reg_no,
        ))

    for u in defaults:
        if u.username not in _memory_users:
            _memory_users[u.username] = u.to_dict()
        if users_col is not None:
            try:
                existing = users_col.find_one({"username": u.username})
                if not existing:
                    users_col.insert_one(u.to_dict())
            except Exception as exc:
                logger.warning(f"Bootstrap user check skipped for {u.username}: {exc}")

    _bootstrapped = True


def log_audit_event(action, actor_username, actor_role, details, status="success", ip_address=""):
    """Record an immutable security/operational audit log entry."""
    entry = {
        "id": secrets.token_hex(8),
        "action": str(action),
        "actor": str(actor_username or "anonymous"),
        "role": str(actor_role or "unauthenticated"),
        "details": str(details or ""),
        "status": str(status),
        "ip_address": str(ip_address or ""),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    _memory_audit_logs.insert(0, entry)
    del _memory_audit_logs[200:]

    _, audit_col = _get_db_collections()
    if audit_col is not None:
        try:
            audit_col.insert_one(dict(entry))
        except Exception:
            pass
    logger.info(f"AUDIT [{entry['status'].upper()}] {entry['action']} by {entry['actor']} ({entry['role']}): {entry['details']}")
    return entry


def get_audit_logs(limit=50):
    """Retrieve recent audit logs."""
    _, audit_col = _get_db_collections()
    if audit_col is not None:
        try:
            cursor = audit_col.find({}, {"_id": 0}).sort("timestamp", -1).limit(int(limit))
            db_logs = list(cursor)
            if db_logs:
                return db_logs
        except Exception:
            pass
    return list(_memory_audit_logs[: int(limit)])


def get_user_by_username(username):
    """Fetch a user record by username. Fails closed in non-test mode if MongoDB is unavailable."""
    uname = str(username or "").strip()
    if not uname:
        return None

    if os.environ.get("STUDENTDB_TEST_MODE") == "1":
        _ensure_bootstrap_users(None)
        mem_doc = _memory_users.get(uname)
        return User.from_dict(mem_doc).to_dict() if mem_doc else None

    users_col, _ = _get_db_collections()
    if users_col is None:
        logger.error(f"Database unavailable while looking up user '{uname}' (failing closed).")
        return None

    _ensure_bootstrap_users(users_col)
    try:
        doc = users_col.find_one({"username": uname})
        if doc:
            return User.from_dict(doc).to_dict()
        return None
    except Exception as exc:
        logger.error(f"Database error looking up user '{uname}': {exc}")
        return None


def authenticate_user(username, password, ip_address=""):
    """Verify username and password, returning public user dict or error."""
    uname = str(username or "").strip()
    if not uname or not password:
        return {"error": "Username and password are required"}

    user_doc = get_user_by_username(uname)
    if not user_doc or not verify_password(user_doc.get("password_hash"), password):
        log_audit_event(
            "LOGIN_FAILED",
            uname,
            "unknown",
            f"Failed login attempt for username '{uname}'",
            status="warning",
            ip_address=ip_address,
        )
        return {"error": "Invalid username or password"}

    if not user_doc.get("is_active", True):
        log_audit_event(
            "LOGIN_BLOCKED",
            uname,
            user_doc.get("role", "Student"),
            "Inactive account login attempt",
            status="warning",
            ip_address=ip_address,
        )
        return {"error": "Account is disabled. Contact an administrator."}

    public_user = User.from_dict(user_doc).to_public_dict()
    log_audit_event(
        "LOGIN_SUCCESS",
        public_user["username"],
        public_user["role"],
        f"Authenticated successfully as {public_user['role']}",
        status="success",
        ip_address=ip_address,
    )
    return {"success": True, "user": public_user}


def create_user(
    username,
    password,
    role="Student",
    full_name="",
    email="",
    assigned_branches=None,
    assigned_reg_nos=None,
    linked_reg_no="",
    actor_username="system",
    actor_role="Admin",
):
    """Create a new platform user with role validation and password strength checks."""
    uname = str(username or "").strip()
    if not uname or not re.match(r"^[A-Za-z0-9_.-]{3,40}$", uname):
        return {"error": "Username must be 3-40 characters (letters, digits, _, ., -)"}

    if role not in User.VALID_ROLES:
        return {"error": f"Role must be one of: {', '.join(sorted(User.VALID_ROLES))}"}

    pwd_err = validate_password_strength(password)
    if pwd_err:
        return {"error": pwd_err}

    if role == "Student" and not str(linked_reg_no or "").strip():
        return {"error": "linked_reg_no is required for Student role accounts"}

    existing = get_user_by_username(uname)
    if existing:
        return {"error": "Username already exists"}

    new_user = User(
        username=uname,
        password_hash=hash_password(password),
        role=role,
        full_name=full_name or uname,
        email=email,
        assigned_branches=assigned_branches or [],
        assigned_reg_nos=assigned_reg_nos or [],
        linked_reg_no=linked_reg_no,
    )

    users_col, _ = _get_db_collections()
    _memory_users[uname] = new_user.to_dict()
    if users_col is not None:
        try:
            users_col.insert_one(new_user.to_dict())
        except Exception as exc:
            logger.error(f"DB user insert error for {uname}: {exc}")

    log_audit_event(
        "USER_CREATED",
        actor_username,
        actor_role,
        f"Created user '{uname}' with role '{role}'",
    )
    return {"success": True, "user": new_user.to_public_dict()}


def list_users():
    """Return public representation of all registered users."""
    users_col, _ = _get_db_collections()
    _ensure_bootstrap_users(users_col)

    results = {}
    for uname, doc in _memory_users.items():
        results[uname] = User.from_dict(doc).to_public_dict()

    if users_col is not None:
        try:
            for doc in users_col.find():
                u = User.from_dict(doc)
                if u:
                    results[u.username] = u.to_public_dict()
        except Exception:
            pass

    return list(results.values())


def reset_user_password(username, current_password, new_password, actor_user=None):
    """Reset a user's password (either self-service with current_password or Admin override) and invalidate older tokens."""
    uname = str(username or "").strip()
    user_doc = get_user_by_username(uname)
    if not user_doc:
        return {"error": "User not found"}

    is_admin_override = actor_user and actor_user.get("role") == "Admin"
    if not is_admin_override:
        if not current_password or not verify_password(user_doc.get("password_hash"), current_password):
            return {"error": "Current password is incorrect"}

    pwd_err = validate_password_strength(new_password)
    if pwd_err:
        return {"error": pwd_err}

    new_hash = hash_password(new_password)
    now_iso = datetime.now(timezone.utc).isoformat()
    valid_after_ts = time.time_ns()

    if os.environ.get("STUDENTDB_TEST_MODE") != "1":
        users_col, _ = _get_db_collections()
        if users_col is None:
            return {"error": "Database unavailable; could not update password"}
        try:
            res = users_col.update_one(
                {"username": uname},
                {
                    "$set": {
                        "password_hash": new_hash,
                        "updated_at": now_iso,
                        "tokens_valid_after": valid_after_ts,
                    }
                },
            )
            if getattr(res, "matched_count", 1) == 0:
                return {"error": "User not found"}
        except Exception as exc:
            logger.error(f"Failed to update password in DB for {uname}: {exc}")
            return {"error": "Database error; could not update password"}

    user_doc["password_hash"] = new_hash
    user_doc["updated_at"] = now_iso
    user_doc["tokens_valid_after"] = valid_after_ts
    _memory_users[uname] = user_doc
    _user_tokens_valid_after[uname] = valid_after_ts

    log_audit_event(
        "PASSWORD_RESET",
        actor_user.get("username") if actor_user else uname,
        actor_user.get("role") if actor_user else user_doc.get("role"),
        f"Password updated and active sessions invalidated for user '{uname}'",
    )
    return {"success": True, "message": "Password updated successfully"}


# ==========================================
# RBAC AUTHORIZATION ENFORCEMENT
# ==========================================
def can_access_student(user, student_doc):
    """Check whether an authenticated user is permitted to view a specific student record."""
    if not user or not student_doc:
        return False

    role = user.get("role")
    if role == "Admin":
        return True

    student_reg = str(student_doc.get("reg_no") or "").strip()
    student_branch = str(student_doc.get("branch") or "").strip().upper()

    if role == "Faculty":
        assigned_branches = [
            str(b).strip().upper() for b in (user.get("assigned_branches") or [])
        ]
        assigned_regs = [
            str(r).strip() for r in (user.get("assigned_reg_nos") or [])
        ]
        if "*" in assigned_branches:
            return True
        if student_branch and student_branch in assigned_branches:
            return True
        if student_reg and student_reg in assigned_regs:
            return True
        return False

    if role == "Student":
        linked_reg = str(user.get("linked_reg_no") or "").strip()
        return Boolean(linked_reg and student_reg and linked_reg == student_reg)

    return False


def Boolean(val):
    return bool(val)


def filter_students_for_user(user, students_list):
    """Filter a list of student dicts to only those the user is authorized to view."""
    if not user or not isinstance(students_list, list):
        return []
    if user.get("role") == "Admin":
        return students_list
    return [s for s in students_list if can_access_student(user, s)]


def can_modify_student(user, student_doc):
    """Check whether an authenticated user is permitted to update a student record."""
    if not user or not student_doc:
        return False
    role = user.get("role")
    if role == "Admin":
        return True
    if role == "Faculty":
        return can_access_student(user, student_doc)
    return False
