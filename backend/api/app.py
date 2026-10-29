import sys
import os
import uuid
from functools import wraps

# =========================
# ADD PROJECT ROOT TO PATH
# =========================
sys.path.append(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../")
    )
)

from flask import (
    Flask,
    Blueprint,
    request,
    jsonify,
    g,
    make_response,
)
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix

from services.student_service import (
    add_student,
    view_students,
    search_student,
    update_student,
    delete_student,
    bulk_delete_students,
    get_student_analytics,
)
from database.db_connection import check_db_readiness
from services.config_validator import (
    validate_environment_config,
    is_production_mode,
)
from services.rate_limit_service import (
    rate_limit,
    clear_rate_limits,
    init_app_rate_limiter,
)
from services.auth_service import (
    authenticate_user,
    create_session_token,
    verify_session_token,
    verify_csrf_token,
    revoke_session_token,
    rotate_csrf_token,
    get_user_by_username,
    create_user,
    list_users,
    reset_user_password,
    can_access_student,
    filter_students_for_user,
    can_modify_student,
    log_audit_event,
    get_audit_logs,
)
from services.academic_service import (
    can_manage_course,
    get_grading_scale,
    update_grading_scale,
    get_course,
    create_course,
    list_courses,
    update_course,
    archive_course,
    enroll_student,
    list_enrollments,
    unenroll_student,
    record_attendance,
    list_attendance,
    get_attendance_report,
    record_grade,
    list_grades,
    calculate_student_gpa,
    get_academic_performance_report,
)
from services.report_service import (
    compute_advanced_analytics,
    build_report_dataset,
    export_report_file,
)
from services.ai_assistant_service import (
    get_ai_assistant_status,
    answer_analytics_question,
)
from logs.logger import logger

SESSION_COOKIE_NAME = "studentdb_session"


# =========================
# RESPONSE & AUTH HELPERS
# =========================
def _error_response(message, status_code=400):
    """Return a consistent JSON error payload containing both 'message' and 'error' keys."""
    return jsonify({
        "success": False,
        "message": message,
        "error": message,
    }), status_code


def _extract_session_from_request():
    """Extract and verify session from HttpOnly cookie or Authorization Bearer header."""
    cookie_token = request.cookies.get(SESSION_COOKIE_NAME)
    if cookie_token:
        payload = verify_session_token(cookie_token)
        if payload:
            return payload, True  # (payload, via_cookie)

    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        bearer_token = auth_header[7:].strip()
        payload = verify_session_token(bearer_token)
        if payload:
            return payload, False

    return None, False


def require_auth(roles=None):
    """Decorator enforcing authentication, CSRF validation on state-changing requests, and RBAC roles."""
    allowed_roles = set(roles) if roles else None

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            session_payload, via_cookie = _extract_session_from_request()
            if not session_payload:
                return _error_response(
                    "Authentication required. Please log in.", 401
                )

            # Enforce CSRF token on state-changing requests
            if request.method in ("POST", "PUT", "DELETE", "PATCH"):
                provided_csrf = request.headers.get("X-CSRF-Token", "")
                if via_cookie and not verify_csrf_token(session_payload, provided_csrf):
                    return _error_response(
                        "CSRF token missing or invalid", 403
                    )

            # Fetch fresh user record to ensure account is still active and roles are up to date
            user_doc = get_user_by_username(session_payload.get("username"))
            if not user_doc or not user_doc.get("is_active", True):
                return _error_response(
                    "User session is no longer valid or account is disabled", 401
                )

            g.current_user = user_doc
            g.session_payload = session_payload

            if allowed_roles and user_doc.get("role") not in allowed_roles:
                log_audit_event(
                    "UNAUTHORIZED_ACCESS",
                    user_doc.get("username"),
                    user_doc.get("role"),
                    f"Forbidden access to {request.method} {request.path}",
                    status="warning",
                    ip_address=request.remote_addr or "",
                )
                return _error_response(
                    f"Access denied. Required role(s): {', '.join(sorted(allowed_roles))}",
                    403,
                )

            return fn(*args, **kwargs)
        return wrapper
    return decorator


def _get_cookie_security_attributes():
    is_https = (
        request.is_secure
        or request.headers.get("X-Forwarded-Proto", "").lower() == "https"
        or os.environ.get("COOKIE_SECURE", "false").lower() in ("1", "true", "yes")
        or is_production_mode()
    )
    raw_samesite = os.environ.get(
        "COOKIE_SAMESITE", "None" if is_https else "Lax"
    ).strip()
    if raw_samesite.lower() == "none" and not is_https:
        samesite_policy = "Lax"
    elif raw_samesite.lower() in ("lax", "strict"):
        samesite_policy = raw_samesite.capitalize()
    elif raw_samesite.lower() == "none":
        samesite_policy = "None"
    else:
        samesite_policy = "Lax"

    try:
        max_age = max(60, min(int(os.environ.get("SESSION_TTL_SECONDS", "28800")), 604800))
    except ValueError:
        max_age = 28800
    return is_https, samesite_policy, max_age


def _set_session_cookie(response, token):
    """Attach HttpOnly, Secure, SameSite session cookie to response."""
    is_https, samesite_policy, max_age = _get_cookie_security_attributes()
    response.set_cookie(
        SESSION_COOKIE_NAME,
        token,
        max_age=max_age,
        httponly=True,
        secure=is_https,
        samesite=samesite_policy,
        path="/",
    )
    return response


# =========================
# BLUEPRINTS
# =========================
public_bp = Blueprint("public", __name__)
auth_bp = Blueprint("auth", __name__)
students_bp = Blueprint("students", __name__)
analytics_bp = Blueprint("analytics", __name__)
users_bp = Blueprint("users", __name__)
academics_bp = Blueprint("academics", __name__)


# -------------------------
# PUBLIC & HEALTH ENDPOINTS
# -------------------------
@public_bp.route("/", methods=["GET"])
def home():
    return jsonify({
        "success": True,
        "message": "Student Management API is running",
        "version": "2.0.0",
    })


@public_bp.route("/health", methods=["GET"])
@public_bp.route("/api/v1/health", methods=["GET"])
@public_bp.route("/health/live", methods=["GET"])
@public_bp.route("/api/v1/health/live", methods=["GET"])
def health_check():
    """Lightweight liveness probe (does not query external dependencies)."""
    return jsonify({
        "success": True,
        "status": "healthy",
        "probe": "liveness",
        "version": "2.0.0",
    }), 200


@public_bp.route("/health/ready", methods=["GET"])
@public_bp.route("/api/v1/health/ready", methods=["GET"])
def readiness_check():
    """Readiness probe verifying database connectivity without leaking sensitive details."""
    readiness = check_db_readiness()
    status_code = 200 if readiness.get("ready") else 503
    return jsonify({
        "success": bool(readiness.get("ready")),
        "status": readiness.get("status", "unavailable"),
        "probe": "readiness",
        "database": readiness.get("database", "disconnected"),
        "version": "2.0.0",
    }), status_code


# -------------------------
# AUTHENTICATION ENDPOINTS
# -------------------------
@auth_bp.route("/auth/login", methods=["POST"])
@auth_bp.route("/api/v1/auth/login", methods=["POST"])
@rate_limit(max_requests=10, window_seconds=60, scope="auth_login")
def login():
    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return _error_response("No JSON data received", 400)

    username = str(data.get("username") or "").strip()
    password = str(data.get("password") or "")

    auth_res = authenticate_user(
        username,
        password,
        ip_address=request.remote_addr or "",
    )
    if "error" in auth_res:
        return _error_response(auth_res["error"], 401)

    user_public = auth_res["user"]
    token, csrf_token = create_session_token(user_public)

    resp = make_response(
        jsonify({
            "success": True,
            "message": "Login successful",
            "user": user_public,
            "csrf_token": csrf_token,
            "session_token": token,
        }),
        200,
    )
    return _set_session_cookie(resp, token)


@auth_bp.route("/auth/logout", methods=["POST"])
@auth_bp.route("/api/v1/auth/logout", methods=["POST"])
def logout():
    session_payload, via_cookie = _extract_session_from_request()
    revoked_ok = True
    if session_payload:
        if via_cookie and not verify_csrf_token(
            session_payload, request.headers.get("X-CSRF-Token", "")
        ):
            return _error_response("CSRF token missing or invalid", 403)
        revoked_ok = revoke_session_token(session_payload)
        log_audit_event(
            "LOGOUT",
            session_payload.get("username"),
            session_payload.get("role"),
            "User logged out and session revoked"
            if revoked_ok
            else "User logged out (revocation store unavailable)",
            status="success" if revoked_ok else "warning",
        )
    else:
        raw_cookie = request.cookies.get(SESSION_COOKIE_NAME)
        if raw_cookie:
            revoked_ok = revoke_session_token(raw_cookie)

    is_https, samesite_policy, _ = _get_cookie_security_attributes()
    status_code = 200 if revoked_ok else 503
    resp = make_response(
        jsonify({
            "success": bool(revoked_ok),
            "message": (
                "Logged out successfully"
                if revoked_ok
                else "Session cookie cleared, but server-side revocation could not be persisted"
            ),
        }),
        status_code,
    )
    resp.delete_cookie(
        SESSION_COOKIE_NAME,
        path="/",
        secure=is_https,
        httponly=True,
        samesite=samesite_policy,
    )
    return resp


@auth_bp.route("/auth/rotate-csrf", methods=["POST"])
@auth_bp.route("/api/v1/auth/rotate-csrf", methods=["POST"])
@rate_limit(max_requests=20, window_seconds=60, scope="csrf_rotate")
@require_auth()
def rotate_csrf_endpoint():
    """Rotate the session and bound CSRF token, revoking the previous token."""
    new_token, new_csrf = rotate_csrf_token(g.session_payload)
    if not new_token or not new_csrf:
        return _error_response("Could not rotate CSRF token", 400)

    resp = make_response(
        jsonify({
            "success": True,
            "message": "CSRF token rotated",
            "csrf_token": new_csrf,
            "session_token": new_token,
        }),
        200,
    )
    return _set_session_cookie(resp, new_token)


@auth_bp.route("/auth/me", methods=["GET"])
@auth_bp.route("/api/v1/auth/me", methods=["GET"])
@require_auth()
def current_user_info():
    user = g.current_user
    session_payload = g.session_payload
    public_profile = {
        "username": user["username"],
        "role": user["role"],
        "full_name": user.get("full_name", user["username"]),
        "email": user.get("email", ""),
        "assigned_branches": user.get("assigned_branches", []),
        "assigned_reg_nos": user.get("assigned_reg_nos", []),
        "linked_reg_no": user.get("linked_reg_no", ""),
    }
    return jsonify({
        "success": True,
        "user": public_profile,
        "csrf_token": session_payload.get("csrf_token"),
    }), 200


@auth_bp.route("/auth/reset-password", methods=["POST"])
@auth_bp.route("/api/v1/auth/reset-password", methods=["POST"])
@rate_limit(max_requests=8, window_seconds=60, scope="password_reset")
@require_auth()
def reset_password_endpoint():
    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return _error_response("No JSON data received", 400)

    target_username = str(
        data.get("username") or g.current_user["username"]
    ).strip()

    # Non-admins can only change their own password
    if (
        g.current_user["role"] != "Admin"
        and target_username != g.current_user["username"]
    ):
        return _error_response("Forbidden: cannot reset another user's password", 403)

    current_password = data.get("current_password", "")
    new_password = data.get("new_password", "")

    res = reset_user_password(
        target_username,
        current_password,
        new_password,
        actor_user=g.current_user,
    )
    if "error" in res:
        return _error_response(res["error"], 400)

    return jsonify(res), 200


# -------------------------
# USER MANAGEMENT (ADMIN)
# -------------------------
@users_bp.route("/api/v1/users", methods=["GET"])
@require_auth(roles=["Admin"])
def get_users_endpoint():
    return jsonify({
        "success": True,
        "users": list_users(),
    }), 200


@users_bp.route("/api/v1/users", methods=["POST"])
@rate_limit(max_requests=20, window_seconds=60, scope="user_create")
@require_auth(roles=["Admin"])
def create_user_endpoint():
    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return _error_response("No JSON data received", 400)

    res = create_user(
        username=data.get("username", ""),
        password=data.get("password", ""),
        role=data.get("role", "Student"),
        full_name=data.get("full_name", ""),
        email=data.get("email", ""),
        assigned_branches=data.get("assigned_branches", []),
        assigned_reg_nos=data.get("assigned_reg_nos", []),
        linked_reg_no=data.get("linked_reg_no", ""),
        actor_username=g.current_user["username"],
        actor_role=g.current_user["role"],
    )
    if "error" in res:
        return _error_response(res["error"], 400)

    return jsonify(res), 201


# -------------------------
# STUDENT ENDPOINTS (PROTECTED + RBAC)
# -------------------------
@students_bp.route("/students", methods=["GET"])
@students_bp.route("/api/v1/students", methods=["GET"])
@require_auth(roles=["Admin", "Faculty", "Student"])
def get_students():
    try:
        search = request.args.get("search")
        branch = request.args.get("branch")
        status = request.args.get("status")
        semester = request.args.get("semester")
        sort_by = request.args.get("sort_by")
        order = request.args.get("order", "asc")

        all_matching = view_students(
            search=search,
            branch=branch,
            status=status,
            semester=semester,
            sort_by=sort_by,
            order=order,
        )

        # Enforce server-side RBAC visibility rules
        students = filter_students_for_user(g.current_user, all_matching)

        page_param = request.args.get("page")
        limit_param = request.args.get("limit")
        if page_param is not None and limit_param is not None:
            try:
                page = max(1, int(page_param))
                limit = max(1, min(200, int(limit_param)))
                total = len(students)
                start = (page - 1) * limit
                end = start + limit
                return jsonify({
                    "success": True,
                    "data": students[start:end],
                    "total": total,
                    "page": page,
                    "limit": limit,
                }), 200
            except ValueError:
                return _error_response("Invalid pagination parameters", 400)

        return jsonify(students), 200

    except Exception as e:
        logger.error(f"GET STUDENTS ERROR: {e}")
        return _error_response("Internal server error while fetching students", 500)


@students_bp.route("/students/<reg_no>", methods=["GET"])
@students_bp.route("/api/v1/students/<reg_no>", methods=["GET"])
@require_auth(roles=["Admin", "Faculty", "Student"])
def get_student(reg_no):
    try:
        # Strict pre-check for Student role so they cannot probe other registration numbers
        if g.current_user["role"] == "Student":
            if str(reg_no).strip() != str(g.current_user.get("linked_reg_no") or "").strip():
                log_audit_event(
                    "UNAUTHORIZED_ACCESS",
                    g.current_user["username"],
                    "Student",
                    f"Attempted to view unauthorized student record '{reg_no}'",
                    status="warning",
                )
                return _error_response(
                    "Access denied: Students may only view their own record", 403
                )

        student = search_student(reg_no)

        if not student:
            return _error_response("Student not found", 404)

        if not can_access_student(g.current_user, student):
            log_audit_event(
                "UNAUTHORIZED_ACCESS",
                g.current_user["username"],
                g.current_user["role"],
                f"Faculty attempted to access unassigned student '{reg_no}' ({student.get('branch')})",
                status="warning",
            )
            return _error_response(
                "Access denied: You are not assigned to this student or branch", 403
            )

        return jsonify(student), 200

    except Exception as e:
        logger.error(f"GET STUDENT ERROR: {e}")
        return _error_response("Internal server error while fetching student", 500)


@students_bp.route("/students", methods=["POST"])
@students_bp.route("/api/v1/students", methods=["POST"])
@require_auth(roles=["Admin"])
def create_student():
    try:
        data = request.get_json(silent=True)

        if not data or not isinstance(data, dict):
            return _error_response("No JSON data received", 400)

        required_fields = [
            "reg_no",
            "roll_no",
            "name",
            "age",
            "branch",
        ]

        for field in required_fields:
            if field not in data or str(data[field]).strip() == "":
                return _error_response(f"{field} is required", 400)

        try:
            age_val = int(data["age"])
        except (ValueError, TypeError):
            return _error_response("age must be a valid integer", 400)

        optional_kwargs = {
            k: data.get(k)
            for k in (
                "email",
                "phone",
                "semester",
                "academic_year",
                "admission_date",
                "status",
                "gpa",
                "attendance_pct",
            )
            if k in data
        }

        result = add_student(
            str(data["reg_no"]),
            str(data["roll_no"]),
            str(data["name"]),
            age_val,
            str(data["branch"]),
            **optional_kwargs,
        )

        if "error" in result:
            return _error_response(result["error"], 400)

        log_audit_event(
            "STUDENT_CREATED",
            g.current_user["username"],
            g.current_user["role"],
            f"Enrolled student {data['reg_no']} in {data['branch']}",
        )

        return jsonify({
            "success": True,
            "message": "Student added successfully",
            "student": result.get("student"),
        }), 201

    except Exception as e:
        logger.error(f"ADD STUDENT ERROR: {e}")
        return _error_response("Internal server error while adding student", 500)


@students_bp.route("/students/<reg_no>", methods=["PUT"])
@students_bp.route("/api/v1/students/<reg_no>", methods=["PUT"])
@require_auth(roles=["Admin", "Faculty"])
def update_student_api(reg_no):
    try:
        data = request.get_json(silent=True)

        if not data or not isinstance(data, dict):
            return _error_response("No JSON data received", 400)

        existing_student = search_student(reg_no)
        if not existing_student:
            return _error_response("Student not found", 404)

        if not can_modify_student(g.current_user, existing_student):
            log_audit_event(
                "UNAUTHORIZED_ACCESS",
                g.current_user["username"],
                g.current_user["role"],
                f"Attempted to update unassigned student '{reg_no}'",
                status="warning",
            )
            return _error_response(
                "Access denied: You are not authorized to modify this student", 403
            )

        # Faculty cannot reassign a student to an unauthorized branch
        if g.current_user["role"] == "Faculty" and "branch" in data:
            new_branch = str(data["branch"] or "").strip().upper()
            old_branch = str(existing_student.get("branch") or "").strip().upper()
            assigned = [
                str(b).strip().upper()
                for b in (g.current_user.get("assigned_branches") or [])
            ]
            if new_branch != old_branch and "*" not in assigned and new_branch not in assigned:
                return _error_response(
                    "Faculty cannot transfer students to an unassigned branch", 403
                )

        for field in ("name", "age", "branch"):
            if field not in data or str(data[field]).strip() == "":
                return _error_response(f"{field} is required", 400)

        try:
            age_val = int(data["age"])
        except (ValueError, TypeError):
            return _error_response("age must be a valid integer", 400)

        optional_kwargs = {
            k: data.get(k)
            for k in (
                "roll_no",
                "email",
                "phone",
                "semester",
                "academic_year",
                "admission_date",
                "status",
                "gpa",
                "attendance_pct",
            )
            if k in data
        }

        result = update_student(
            reg_no,
            str(data["name"]),
            age_val,
            str(data["branch"]),
            **optional_kwargs,
        )

        if "error" in result:
            status_code = 404 if result["error"] == "Student not found" else 400
            return _error_response(result["error"], status_code)

        log_audit_event(
            "STUDENT_UPDATED",
            g.current_user["username"],
            g.current_user["role"],
            f"Updated student {reg_no} ({data['name']})",
        )

        return jsonify({
            "success": True,
            "message": "Student updated successfully",
        }), 200

    except Exception as e:
        logger.error(f"UPDATE ERROR: {e}")
        return _error_response("Internal server error while updating student", 500)


@students_bp.route("/students/<reg_no>", methods=["DELETE"])
@students_bp.route("/api/v1/students/<reg_no>", methods=["DELETE"])
@require_auth(roles=["Admin"])
def delete_student_api(reg_no):
    try:
        result = delete_student(reg_no)

        if "error" in result:
            return _error_response(result["error"], 404)

        log_audit_event(
            "STUDENT_DELETED",
            g.current_user["username"],
            g.current_user["role"],
            f"Deleted student record '{reg_no}'",
        )

        return jsonify({
            "success": True,
            "message": "Student deleted successfully",
        }), 200

    except Exception as e:
        logger.error(f"DELETE ERROR: {e}")
        return _error_response("Internal server error while deleting student", 500)


@students_bp.route("/students/bulk-delete", methods=["POST"])
@students_bp.route("/api/v1/students/bulk-delete", methods=["POST"])
@rate_limit(max_requests=15, window_seconds=60, scope="students_bulk_delete")
@require_auth(roles=["Admin"])
def bulk_delete_api():
    try:
        data = request.get_json(silent=True) or {}
        reg_nos = data.get("reg_nos", [])
        result = bulk_delete_students(reg_nos)

        if "error" in result:
            return _error_response(result["error"], 400)

        log_audit_event(
            "BULK_DELETE",
            g.current_user["username"],
            g.current_user["role"],
            f"Bulk deleted {result.get('deleted_count', 0)} student record(s)",
        )

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"BULK DELETE ERROR: {e}")
        return _error_response("Internal server error during bulk delete", 500)


@students_bp.route("/students/bulk-import", methods=["POST"])
@students_bp.route("/api/v1/students/bulk-import", methods=["POST"])
@rate_limit(max_requests=10, window_seconds=60, scope="students_bulk_import")
@require_auth(roles=["Admin"])
def bulk_import_api():
    try:
        data = request.get_json(silent=True) or {}
        records = data.get("students", [])

        if not isinstance(records, list) or not records:
            return _error_response("A non-empty 'students' list is required", 400)

        added = 0
        skipped = 0
        errors = []

        for idx, item in enumerate(records, start=1):
            if not isinstance(item, dict):
                skipped += 1
                errors.append(f"Row {idx}: Invalid record format")
                continue

            optional_kwargs = {
                k: item.get(k)
                for k in (
                    "email",
                    "phone",
                    "semester",
                    "academic_year",
                    "admission_date",
                    "status",
                    "gpa",
                    "attendance_pct",
                )
                if k in item
            }

            res = add_student(
                item.get("reg_no", ""),
                item.get("roll_no", ""),
                item.get("name", ""),
                item.get("age", 0),
                item.get("branch", ""),
                **optional_kwargs,
            )

            if "error" in res:
                skipped += 1
                errors.append(f"Row {idx} ({item.get('reg_no', 'N/A')}): {res['error']}")
            else:
                added += 1

        log_audit_event(
            "BULK_IMPORT",
            g.current_user["username"],
            g.current_user["role"],
            f"Imported {added} student(s), skipped {skipped}",
        )

        return jsonify({
            "success": True,
            "added": added,
            "skipped": skipped,
            "errors": errors,
            "message": f"Imported {added} student(s), skipped {skipped}.",
        }), 200

    except Exception as e:
        logger.error(f"BULK IMPORT ERROR: {e}")
        return _error_response("Internal server error during bulk import", 500)


# -------------------------
# ANALYTICS & AUDIT LOGS
# -------------------------
@analytics_bp.route("/stats", methods=["GET"])
@analytics_bp.route("/api/v1/analytics/summary", methods=["GET"])
@require_auth(roles=["Admin", "Faculty"])
def get_stats():
    try:
        all_students = view_students()
        scoped_students = filter_students_for_user(g.current_user, all_students)
        analytics = get_student_analytics(students_subset=scoped_students)
        return jsonify({
            "success": True,
            **analytics,
        }), 200
    except Exception as e:
        logger.error(f"GET STATS ERROR: {e}")
        return _error_response("Failed to compute analytics", 500)


@analytics_bp.route("/api/v1/logs", methods=["GET"])
@require_auth(roles=["Admin"])
def get_audit_logs_endpoint():
    limit = request.args.get("limit", 50)
    try:
        limit_val = max(1, min(200, int(limit)))
    except ValueError:
        limit_val = 50
    return jsonify({
        "success": True,
        "logs": get_audit_logs(limit=limit_val),
    }), 200


@analytics_bp.route("/api/v1/analytics/advanced", methods=["GET"])
@require_auth(roles=["Admin", "Faculty", "Student"])
@rate_limit(max_requests=40, window_seconds=60, scope="analytics_advanced")
def get_advanced_analytics_endpoint():
    try:
        res = compute_advanced_analytics(
            g.current_user, request.args.to_dict()
        )
        if "error" in res:
            return _error_response(res["error"], res.get("status_code", 400))
        return jsonify(res), 200
    except Exception as e:
        logger.error(f"ADVANCED ANALYTICS ERROR: {e}")
        return _error_response("Failed to compute advanced analytics", 500)


@analytics_bp.route("/api/v1/reports/preview", methods=["GET"])
@require_auth(roles=["Admin", "Faculty", "Student"])
@rate_limit(max_requests=40, window_seconds=60, scope="reports_preview")
def preview_report_endpoint():
    try:
        res = build_report_dataset(g.current_user, request.args.to_dict())
        if "error" in res:
            return _error_response(res["error"], res.get("status_code", 400))
        return jsonify(res), 200
    except Exception as e:
        logger.error(f"REPORT PREVIEW ERROR: {e}")
        return _error_response("Failed to generate report preview", 500)


@analytics_bp.route("/api/v1/reports/export", methods=["GET", "POST"])
@require_auth(roles=["Admin", "Faculty", "Student"])
@rate_limit(max_requests=25, window_seconds=60, scope="reports_export")
def export_report_endpoint():
    try:
        if request.method == "POST":
            raw_filters = request.get_json(silent=True) or {}
        else:
            raw_filters = request.args.to_dict()

        res = export_report_file(g.current_user, raw_filters)
        if "error" in res:
            if res.get("status_code") == 403:
                log_audit_event(
                    "UNAUTHORIZED_EXPORT_ATTEMPT",
                    g.current_user["username"],
                    g.current_user["role"],
                    f"Blocked unauthorized report export ({raw_filters.get('report_type', 'unknown')})",
                    status="warning",
                )
            return _error_response(res["error"], res.get("status_code", 400))

        log_audit_event(
            "REPORT_EXPORTED",
            g.current_user["username"],
            g.current_user["role"],
            f"Exported {res['report_type']} ({res['row_count']} rows) as {res['filename']}",
        )

        response = make_response(res["content"], 200)
        response.headers["Content-Type"] = res["mimetype"]
        response.headers["Content-Disposition"] = (
            f'attachment; filename="{res["filename"]}"'
        )
        return response
    except Exception as e:
        logger.error(f"REPORT EXPORT ERROR: {e}")
        return _error_response("Failed to export report file", 500)


@analytics_bp.route("/api/v1/ai/status", methods=["GET"])
@require_auth(roles=["Admin", "Faculty", "Student"])
def ai_assistant_status_endpoint():
    return jsonify(get_ai_assistant_status()), 200


@analytics_bp.route("/api/v1/ai/query", methods=["POST"])
@require_auth(roles=["Admin", "Faculty", "Student"])
@rate_limit(max_requests=20, window_seconds=60, scope="ai_query")
def ai_assistant_query_endpoint():
    try:
        data = request.get_json(silent=True)
        if not data or not isinstance(data, dict):
            return _error_response("No JSON data received", 400)

        question = data.get("question", "")
        filters = data.get("filters") if isinstance(data.get("filters"), dict) else {}

        res = answer_analytics_question(
            g.current_user, question=question, raw_filters=filters
        )
        if "error" in res:
            if res.get("status_code") == 403:
                log_audit_event(
                    "UNAUTHORIZED_AI_QUERY",
                    g.current_user["username"],
                    g.current_user["role"],
                    "Blocked AI query outside user RBAC scope",
                    status="warning",
                )
            return _error_response(res["error"], res.get("status_code", 400))

        log_audit_event(
            "AI_ANALYTICS_QUERY",
            g.current_user["username"],
            g.current_user["role"],
            f"Executed grounded AI query (intent={res.get('intent')}, blocked={res.get('action_blocked')})",
        )
        return jsonify(res), 200
    except Exception as e:
        logger.error(f"AI QUERY ERROR: {e}")
        return _error_response("Failed to process AI analytics query", 500)


# -------------------------
# ACADEMIC MANAGEMENT ENDPOINTS (COURSES, ENROLLMENTS, ATTENDANCE, GRADES)
# -------------------------
@academics_bp.route("/api/v1/academics/grading-scale", methods=["GET"])
@require_auth(roles=["Admin", "Faculty", "Student"])
def get_grading_scale_endpoint():
    scale = get_grading_scale()
    return jsonify({
        "success": True,
        "grading_scale": scale.to_dict(),
    }), 200


@academics_bp.route("/api/v1/academics/grading-scale", methods=["PUT"])
@require_auth(roles=["Admin"])
def update_grading_scale_endpoint():
    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return _error_response("No JSON data received", 400)

    res = update_grading_scale(data)
    if "error" in res:
        return _error_response(res["error"], 400)

    log_audit_event(
        "GRADING_SCALE_UPDATED",
        g.current_user["username"],
        g.current_user["role"],
        f"Updated grading scale '{res['grading_scale'].get('scale_name')}'",
    )
    return jsonify(res), 200


@academics_bp.route("/api/v1/courses", methods=["GET"])
@require_auth(roles=["Admin", "Faculty", "Student"])
def get_courses_endpoint():
    branch = request.args.get("branch")
    semester = request.args.get("semester")
    status = request.args.get("status")
    include_archived = request.args.get("include_archived", "false").lower() in (
        "1",
        "true",
        "yes",
    )
    courses = list_courses(
        user=g.current_user,
        branch=branch,
        semester=semester,
        status=status,
        include_archived=include_archived,
    )
    return jsonify({
        "success": True,
        "courses": courses,
    }), 200


@academics_bp.route("/api/v1/courses/<course_code>", methods=["GET"])
@require_auth(roles=["Admin", "Faculty", "Student"])
def get_single_course_endpoint(course_code):
    course = get_course(course_code)
    if not course:
        return _error_response("Course not found", 404)
    if g.current_user["role"] == "Faculty" and not can_manage_course(
        g.current_user, course
    ):
        return _error_response(
            "Access denied: You are not assigned to this course", 403
        )
    return jsonify({
        "success": True,
        "course": course,
    }), 200


@academics_bp.route("/api/v1/courses", methods=["POST"])
@require_auth(roles=["Admin"])
def create_course_endpoint():
    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return _error_response("No JSON data received", 400)

    res = create_course(
        course_code=data.get("course_code", ""),
        course_name=data.get("course_name", ""),
        branch=data.get("branch", ""),
        credits=data.get("credits", 3),
        semester=data.get("semester", "1"),
        academic_year=data.get("academic_year", "2025-2026"),
        faculty_username=data.get("faculty_username", ""),
        capacity=data.get("capacity", 60),
        description=data.get("description", ""),
    )
    if "error" in res:
        return _error_response(res["error"], 400)

    log_audit_event(
        "COURSE_CREATED",
        g.current_user["username"],
        g.current_user["role"],
        f"Created course {res['course']['course_code']} ({res['course']['course_name']})",
    )
    return jsonify(res), 201


@academics_bp.route("/api/v1/courses/<course_code>", methods=["PUT"])
@require_auth(roles=["Admin"])
def update_course_endpoint(course_code):
    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return _error_response("No JSON data received", 400)

    res = update_course(course_code, **data)
    if "error" in res:
        status_code = 404 if res["error"] == "Course not found" else 400
        return _error_response(res["error"], status_code)

    log_audit_event(
        "COURSE_UPDATED",
        g.current_user["username"],
        g.current_user["role"],
        f"Updated course {course_code}",
    )
    return jsonify(res), 200


@academics_bp.route("/api/v1/courses/<course_code>/archive", methods=["PATCH"])
@require_auth(roles=["Admin"])
def archive_course_endpoint(course_code):
    data = request.get_json(silent=True) or {}
    archive_flag = bool(data.get("archive", True))
    res = archive_course(course_code, archive=archive_flag)
    if "error" in res:
        status_code = 404 if res["error"] == "Course not found" else 400
        return _error_response(res["error"], status_code)

    log_audit_event(
        "COURSE_ARCHIVED" if archive_flag else "COURSE_RESTORED",
        g.current_user["username"],
        g.current_user["role"],
        f"{'Archived' if archive_flag else 'Restored'} course {course_code}",
    )
    return jsonify(res), 200


# -------------------------
# ENROLLMENT ENDPOINTS
# -------------------------
@academics_bp.route("/api/v1/enrollments", methods=["GET"])
@require_auth(roles=["Admin", "Faculty", "Student"])
def get_enrollments_endpoint():
    reg_no = request.args.get("reg_no")
    course_code = request.args.get("course_code")
    semester = request.args.get("semester")

    if g.current_user["role"] == "Student":
        linked = str(g.current_user.get("linked_reg_no") or "").strip()
        if reg_no and str(reg_no).strip() != linked:
            return _error_response(
                "Access denied: Students may only view their own enrollments", 403
            )
        reg_no = linked

    if g.current_user["role"] == "Faculty" and course_code:
        course = get_course(course_code)
        if not course or not can_manage_course(g.current_user, course):
            return _error_response(
                "Access denied: You are not assigned to this course", 403
            )

    enrollments = list_enrollments(
        user=g.current_user,
        reg_no=reg_no,
        course_code=course_code,
        semester=semester,
    )
    return jsonify({
        "success": True,
        "enrollments": enrollments,
    }), 200


@academics_bp.route("/api/v1/enrollments", methods=["POST"])
@require_auth(roles=["Admin", "Faculty"])
def create_enrollment_endpoint():
    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return _error_response("No JSON data received", 400)

    course_code = str(data.get("course_code") or "").strip().upper()
    course = get_course(course_code)
    if not course:
        return _error_response(f"Course '{course_code}' not found", 404)

    if g.current_user["role"] == "Faculty" and not can_manage_course(
        g.current_user, course
    ):
        return _error_response(
            "Access denied: Faculty may only enroll students into their assigned courses",
            403,
        )

    res = enroll_student(
        reg_no=data.get("reg_no", ""),
        course_code=course_code,
        semester=data.get("semester"),
        academic_year=data.get("academic_year"),
        enrolled_by=g.current_user["username"],
    )
    if "error" in res:
        status_code = 404 if "not found" in res["error"].lower() else 400
        return _error_response(res["error"], status_code)

    log_audit_event(
        "STUDENT_ENROLLED",
        g.current_user["username"],
        g.current_user["role"],
        f"Enrolled {data.get('reg_no')} in {course_code}",
    )
    return jsonify(res), 201


@academics_bp.route("/api/v1/enrollments/<path:enrollment_id>", methods=["DELETE"])
@require_auth(roles=["Admin"])
def delete_enrollment_endpoint(enrollment_id):
    res = unenroll_student(enrollment_id)
    if "error" in res:
        return _error_response(res["error"], 404)

    log_audit_event(
        "STUDENT_UNENROLLED",
        g.current_user["username"],
        g.current_user["role"],
        f"Removed enrollment {enrollment_id}",
    )
    return jsonify(res), 200


# -------------------------
# ATTENDANCE ENDPOINTS
# -------------------------
@academics_bp.route("/api/v1/attendance", methods=["GET"])
@require_auth(roles=["Admin", "Faculty", "Student"])
def get_attendance_endpoint():
    reg_no = request.args.get("reg_no")
    course_code = request.args.get("course_code")
    date = request.args.get("date")

    if g.current_user["role"] == "Student":
        linked = str(g.current_user.get("linked_reg_no") or "").strip()
        if reg_no and str(reg_no).strip() != linked:
            return _error_response(
                "Access denied: Students may only view their own attendance", 403
            )
        reg_no = linked

    if g.current_user["role"] == "Faculty" and course_code:
        course = get_course(course_code)
        if not course or not can_manage_course(g.current_user, course):
            return _error_response(
                "Access denied: You are not assigned to this course", 403
            )

    records = list_attendance(
        user=g.current_user,
        reg_no=reg_no,
        course_code=course_code,
        date=date,
    )
    return jsonify({
        "success": True,
        "attendance": records,
    }), 200


@academics_bp.route("/api/v1/attendance", methods=["POST"])
@require_auth(roles=["Admin", "Faculty"])
def create_attendance_endpoint():
    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return _error_response("No JSON data received", 400)

    course_code = str(data.get("course_code") or "").strip().upper()
    course = get_course(course_code)
    if not course:
        return _error_response(f"Course '{course_code}' not found", 404)

    if not can_manage_course(g.current_user, course):
        return _error_response(
            "Access denied: You are not assigned to record attendance for this course",
            403,
        )

    res = record_attendance(
        reg_no=data.get("reg_no", ""),
        course_code=course_code,
        date=data.get("date", ""),
        status=data.get("status", "Present"),
        session=data.get("session", "Lecture"),
        remarks=data.get("remarks", ""),
        recorded_by=g.current_user["username"],
        allow_update=False,
    )
    if "error" in res:
        status_code = 404 if "not found" in res["error"].lower() else 400
        return _error_response(res["error"], status_code)

    log_audit_event(
        "ATTENDANCE_RECORDED",
        g.current_user["username"],
        g.current_user["role"],
        f"Marked {data.get('reg_no')} as {data.get('status', 'Present')} in {course_code} on {data.get('date')}",
    )
    return jsonify(res), 201


@academics_bp.route("/api/v1/attendance", methods=["PUT"])
@require_auth(roles=["Admin", "Faculty"])
def update_attendance_endpoint():
    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return _error_response("No JSON data received", 400)

    course_code = str(data.get("course_code") or "").strip().upper()
    course = get_course(course_code)
    if not course:
        return _error_response(f"Course '{course_code}' not found", 404)

    if not can_manage_course(g.current_user, course):
        return _error_response(
            "Access denied: You are not assigned to update attendance for this course",
            403,
        )

    res = record_attendance(
        reg_no=data.get("reg_no", ""),
        course_code=course_code,
        date=data.get("date", ""),
        status=data.get("status", "Present"),
        session=data.get("session", "Lecture"),
        remarks=data.get("remarks", ""),
        recorded_by=g.current_user["username"],
        allow_update=True,
    )
    if "error" in res:
        return _error_response(res["error"], 400)

    return jsonify(res), 200


@academics_bp.route("/api/v1/attendance/batch", methods=["POST"])
@rate_limit(max_requests=30, window_seconds=60, scope="attendance_batch")
@require_auth(roles=["Admin", "Faculty"])
def batch_attendance_endpoint():
    data = request.get_json(silent=True) or {}
    course_code = str(data.get("course_code") or "").strip().upper()
    date = str(data.get("date") or "").strip()
    session = str(data.get("session") or "Lecture").strip()
    allow_update = bool(data.get("allow_update", True))
    entries = data.get("records", [])

    if not course_code or not date or not isinstance(entries, list) or not entries:
        return _error_response(
            "course_code, date, and a non-empty 'records' list are required", 400
        )

    course = get_course(course_code)
    if not course:
        return _error_response(f"Course '{course_code}' not found", 404)

    if not can_manage_course(g.current_user, course):
        return _error_response(
            "Access denied: You are not assigned to this course", 403
        )

    saved = 0
    errors = []
    for item in entries:
        res = record_attendance(
            reg_no=item.get("reg_no", ""),
            course_code=course_code,
            date=date,
            status=item.get("status", "Present"),
            session=session,
            remarks=item.get("remarks", ""),
            recorded_by=g.current_user["username"],
            allow_update=allow_update,
        )
        if "error" in res:
            errors.append(res["error"])
        else:
            saved += 1

    log_audit_event(
        "BATCH_ATTENDANCE",
        g.current_user["username"],
        g.current_user["role"],
        f"Recorded batch attendance for {saved} student(s) in {course_code} on {date}",
    )
    return jsonify({
        "success": True,
        "saved": saved,
        "errors": errors,
        "message": f"Recorded attendance for {saved} student(s)",
    }), 200


@academics_bp.route("/api/v1/attendance/report", methods=["GET"])
@require_auth(roles=["Admin", "Faculty", "Student"])
def attendance_report_endpoint():
    reg_no = request.args.get("reg_no")
    course_code = request.args.get("course_code")

    if g.current_user["role"] == "Student":
        linked = str(g.current_user.get("linked_reg_no") or "").strip()
        if reg_no and str(reg_no).strip() != linked:
            return _error_response(
                "Access denied: Students may only view their own attendance report",
                403,
            )
        reg_no = linked

    if g.current_user["role"] == "Faculty" and course_code:
        course = get_course(course_code)
        if not course or not can_manage_course(g.current_user, course):
            return _error_response(
                "Access denied: You are not assigned to this course", 403
            )

    report = get_attendance_report(
        user=g.current_user,
        course_code=course_code,
        reg_no=reg_no,
    )
    return jsonify({
        "success": True,
        **report,
    }), 200


# -------------------------
# GRADES & GPA ENDPOINTS
# -------------------------
@academics_bp.route("/api/v1/grades", methods=["GET"])
@require_auth(roles=["Admin", "Faculty", "Student"])
def get_grades_endpoint():
    reg_no = request.args.get("reg_no")
    course_code = request.args.get("course_code")
    semester = request.args.get("semester")

    if g.current_user["role"] == "Student":
        linked = str(g.current_user.get("linked_reg_no") or "").strip()
        if reg_no and str(reg_no).strip() != linked:
            return _error_response(
                "Access denied: Students may only view their own grades", 403
            )
        reg_no = linked

    if g.current_user["role"] == "Faculty" and course_code:
        course = get_course(course_code)
        if not course or not can_manage_course(g.current_user, course):
            return _error_response(
                "Access denied: You are not assigned to this course", 403
            )

    grades = list_grades(
        user=g.current_user,
        reg_no=reg_no,
        course_code=course_code,
        semester=semester,
    )
    return jsonify({
        "success": True,
        "grades": grades,
    }), 200


@academics_bp.route("/api/v1/grades", methods=["POST"])
@require_auth(roles=["Admin", "Faculty"])
def create_grade_endpoint():
    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return _error_response("No JSON data received", 400)

    course_code = str(data.get("course_code") or "").strip().upper()
    course = get_course(course_code)
    if not course:
        return _error_response(f"Course '{course_code}' not found", 404)

    if not can_manage_course(g.current_user, course):
        return _error_response(
            "Access denied: You are not assigned to record grades for this course",
            403,
        )

    res = record_grade(
        reg_no=data.get("reg_no", ""),
        course_code=course_code,
        assessment_type=data.get("assessment_type", "Overall"),
        marks_obtained=data.get("marks_obtained", 0),
        max_marks=data.get("max_marks", 100),
        semester=data.get("semester"),
        academic_year=data.get("academic_year"),
        recorded_by=g.current_user["username"],
        allow_update=False,
    )
    if "error" in res:
        status_code = 404 if "not found" in res["error"].lower() else 400
        return _error_response(res["error"], status_code)

    log_audit_event(
        "GRADE_RECORDED",
        g.current_user["username"],
        g.current_user["role"],
        f"Recorded grade for {data.get('reg_no')} in {course_code} ({data.get('assessment_type', 'Overall')})",
    )
    return jsonify(res), 201


@academics_bp.route("/api/v1/grades", methods=["PUT"])
@require_auth(roles=["Admin", "Faculty"])
def update_grade_endpoint():
    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return _error_response("No JSON data received", 400)

    course_code = str(data.get("course_code") or "").strip().upper()
    course = get_course(course_code)
    if not course:
        return _error_response(f"Course '{course_code}' not found", 404)

    if not can_manage_course(g.current_user, course):
        return _error_response(
            "Access denied: You are not assigned to update grades for this course",
            403,
        )

    res = record_grade(
        reg_no=data.get("reg_no", ""),
        course_code=course_code,
        assessment_type=data.get("assessment_type", "Overall"),
        marks_obtained=data.get("marks_obtained", 0),
        max_marks=data.get("max_marks", 100),
        semester=data.get("semester"),
        academic_year=data.get("academic_year"),
        recorded_by=g.current_user["username"],
        allow_update=True,
    )
    if "error" in res:
        return _error_response(res["error"], 400)

    return jsonify(res), 200


@academics_bp.route("/api/v1/grades/gpa/<reg_no>", methods=["GET"])
@require_auth(roles=["Admin", "Faculty", "Student"])
def student_gpa_endpoint(reg_no):
    if g.current_user["role"] == "Student":
        linked = str(g.current_user.get("linked_reg_no") or "").strip()
        if str(reg_no).strip() != linked:
            return _error_response(
                "Access denied: Students may only view their own GPA", 403
            )

    student = search_student(reg_no)
    if not student:
        return _error_response("Student not found", 404)

    if not can_access_student(g.current_user, student):
        return _error_response(
            "Access denied: You are not assigned to this student", 403
        )

    semester = request.args.get("semester")
    summary = calculate_student_gpa(reg_no, semester=semester)
    return jsonify({
        "success": True,
        **summary,
    }), 200


@academics_bp.route("/api/v1/grades/report", methods=["GET"])
@require_auth(roles=["Admin", "Faculty", "Student"])
def grades_report_endpoint():
    reg_no = request.args.get("reg_no")
    course_code = request.args.get("course_code")

    if g.current_user["role"] == "Student":
        linked = str(g.current_user.get("linked_reg_no") or "").strip()
        if reg_no and str(reg_no).strip() != linked:
            return _error_response(
                "Access denied: Students may only view their own performance report",
                403,
            )
        reg_no = linked

    if g.current_user["role"] == "Faculty" and course_code:
        course = get_course(course_code)
        if not course or not can_manage_course(g.current_user, course):
            return _error_response(
                "Access denied: You are not assigned to this course", 403
            )

    report = get_academic_performance_report(
        user=g.current_user,
        course_code=course_code,
        reg_no=reg_no,
    )
    return jsonify({
        "success": True,
        **report,
    }), 200


# =========================
# APPLICATION FACTORY
# =========================
def create_app(
    validate_config=True,
    ratelimit_storage_uri=None,
    ratelimit_storage_backend=None,
):
    if validate_config:
        validate_environment_config(
            raise_on_error=is_production_mode()
        )

    application = Flask(__name__)

    # Trust exactly TRUSTED_PROXY_HOPS reverse proxies (Render's edge = 1 by default)
    # for X-Forwarded-For / X-Forwarded-Proto. This makes request.remote_addr the
    # proxy-observed client IP (not a client-spoofable header value) and
    # request.is_secure reflect the original HTTPS scheme.
    try:
        proxy_hops = max(0, min(int(os.environ.get("TRUSTED_PROXY_HOPS", "1")), 5))
    except ValueError:
        proxy_hops = 1
    if proxy_hops:
        application.wsgi_app = ProxyFix(
            application.wsgi_app, x_for=proxy_hops, x_proto=proxy_hops
        )
    init_app_rate_limiter(
        application,
        storage_uri=ratelimit_storage_uri,
        storage_backend=ratelimit_storage_backend,
    )

    cors_origins_env = os.environ.get(
        "CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000,https://student-database-management-l3pl.onrender.com",
    ).strip()

    cors_origins = [
        o.strip()
        for o in cors_origins_env.split(",")
        if o.strip() and o.strip() != "*"
    ] or [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    CORS(
        application,
        supports_credentials=True,
        resources={
            r"/*": {
                "origins": cors_origins,
                "allow_headers": ["Content-Type", "Authorization", "X-CSRF-Token"],
                "expose_headers": [
                    "X-Request-ID",
                    "Retry-After",
                    "X-RateLimit-Limit",
                    "X-RateLimit-Remaining",
                    "X-RateLimit-Reset",
                    "Content-Disposition",
                ],
            }
        },
    )

    @application.before_request
    def attach_request_id():
        g.request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

    @application.after_request
    def add_security_headers(response):
        response.headers["X-Request-ID"] = getattr(g, "request_id", "")
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=()"
        )
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; frame-ancestors 'none'"
        )
        if (
            request.is_secure
            or request.headers.get("X-Forwarded-Proto", "").lower() == "https"
            or is_production_mode()
        ):
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        if request.path.startswith(("/api/", "/auth/", "/students")):
            response.headers.setdefault("Cache-Control", "no-store")
        return response

    application.register_blueprint(public_bp)
    application.register_blueprint(auth_bp)
    application.register_blueprint(students_bp)
    application.register_blueprint(analytics_bp)
    application.register_blueprint(users_bp)
    application.register_blueprint(academics_bp)

    return application


app = create_app()


# =========================
# MAIN
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() in ("1", "true", "yes")

    app.run(
        host="0.0.0.0",
        port=port,
        debug=debug_mode,
    )
