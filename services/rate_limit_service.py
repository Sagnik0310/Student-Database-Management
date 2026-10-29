"""
Distributed, Flask-Limiter-backed rate limiting service for
Student Database Management System 2.0.

Key security properties:
1. Configurable shared storage via `RATELIMIT_STORAGE_URI` (supports `redis://`,
   `rediss://`, `mongodb://`, `mongodb+srv://`, and `memory://` in local dev/tests).
2. Each `create_app()` instance initializes its own `Flask-Limiter` (`Limiter`)
   and `MovingWindowRateLimiter` bound to the configured storage backend — never
   relying on process-local global dictionaries across Gunicorn workers.
3. Fail-Closed Production Policy: In production (or when `RATELIMIT_FAIL_CLOSED=true`),
   `memory://` is forbidden and any storage unavailability/error rejects protected
   requests with HTTP 503 rather than silently falling back to per-worker counters
   or unrestricted access.
4. Privacy-Safe Keys: Rate-limit keys use only the endpoint scope and a truncated
   SHA-256 digest of the client IP (`rl:<scope>:<sha256_ip>`), never storing
   passwords, cookies, session tokens, CSRF tokens, or student PII.
"""

from __future__ import annotations

import hashlib
import os
import time
from functools import wraps
from typing import Any, Callable, Mapping, Optional, Tuple

from flask import Flask, current_app, g, jsonify, make_response, request
from flask_limiter import Limiter
from limits import RateLimitItemPerSecond
from limits.storage import MemoryStorage, Storage, storage_from_string
from limits.strategies import MovingWindowRateLimiter

from logs.logger import logger
from services.auth_service import log_audit_event
from services.config_validator import is_production_mode

# Optional test hook allowing tests to register a shared simulated backend for a URI
# (e.g. "redis://shared-test-cluster:6379/0") without requiring a live Redis daemon.
_custom_storage_registry: dict[str, Storage] = {}
_active_test_storages: list[Storage] = []


def register_shared_test_storage(uri: str, storage_instance: Optional[Storage] = None) -> Storage:
    """
    Register a shared `limits.storage.Storage` instance for a given URI so
    multiple independently initialized `create_app()` instances connect to the
    same underlying store during multi-worker tests.
    """
    store = storage_instance if storage_instance is not None else MemoryStorage()
    _custom_storage_registry[uri] = store
    if store not in _active_test_storages:
        _active_test_storages.append(store)
    return store


def unregister_shared_test_storage(uri: Optional[str] = None) -> None:
    if uri is None:
        _custom_storage_registry.clear()
    else:
        _custom_storage_registry.pop(uri, None)


def extract_client_ip() -> str:
    """
    Return the client IP as resolved by Werkzeug ProxyFix (configured in create_app()
    with TRUSTED_PROXY_HOPS). ProxyFix takes the right-most X-Forwarded-For entry
    appended by the trusted proxy, so a client-supplied (left-most) value cannot be
    used to rotate identities and bypass rate limits.
    """
    return (request.remote_addr or "127.0.0.1").strip()


def build_rate_limit_key(scope: str = "api", client_ip: Optional[str] = None) -> Tuple[str, str]:
    """
    Build a privacy-safe rate-limit key containing only the scope and a one-way
    SHA-256 hash of the client IP. Never includes passwords, tokens, cookies, or PII.
    """
    raw_ip = (client_ip if client_ip is not None else extract_client_ip()) or "127.0.0.1"
    ip_digest = hashlib.sha256(raw_ip.encode("utf-8")).hexdigest()[:20]
    safe_scope = "".join(ch for ch in str(scope or "api") if ch.isalnum() or ch in ("_", "-"))
    return f"rl:{safe_scope}:{ip_digest}", raw_ip


def _flask_limiter_key_func() -> str:
    key, _ = build_rate_limit_key("global")
    return key


def resolve_ratelimit_storage_uri(
    env: Optional[Mapping[str, str]] = None,
    strict_production: Optional[bool] = None,
) -> str:
    """
    Determine the effective storage URI for Flask-Limiter / limits.
    In production, process-local `memory://` is forbidden; requires `RATELIMIT_STORAGE_URI`
    (or `REDIS_URL`), or falls back to shared `MONGO_URI`.
    """
    source = env if env is not None else os.environ
    prod = (
        bool(strict_production)
        if strict_production is not None
        else is_production_mode(source)
    )

    configured_uri = str(
        source.get("RATELIMIT_STORAGE_URI") or source.get("REDIS_URL") or ""
    ).strip()

    if prod:
        if configured_uri:
            if configured_uri.lower().startswith("memory://"):
                raise RuntimeError(
                    "In-memory rate limiting ('memory://') is forbidden in production."
                )
            if not configured_uri.startswith(
                ("redis://", "rediss://", "mongodb://", "mongodb+srv://")
            ):
                raise RuntimeError(
                    "Invalid RATELIMIT_STORAGE_URI scheme in production."
                )
            return configured_uri

        mongo_uri = str(source.get("MONGO_URI") or "").strip()
        if mongo_uri.startswith(("mongodb://", "mongodb+srv://")):
            return mongo_uri

        raise RuntimeError(
            "Distributed rate limiting is required in production, but neither RATELIMIT_STORAGE_URI nor MONGO_URI is configured."
        )

    # Non-production (development or STUDENTDB_TEST_MODE=1)
    if configured_uri:
        return configured_uri
    return "memory://"


def should_fail_closed(env: Optional[Mapping[str, str]] = None) -> bool:
    """
    Determine whether rate-limiter backend failures must reject protected requests (HTTP 503).
    Always True in production. In non-production, defaults to True (never silently fall back
    to unrestricted requests or independent per-worker counters) unless RATELIMIT_FAIL_CLOSED
    is explicitly set to 'false'.
    """
    source = env if env is not None else os.environ
    if is_production_mode(source):
        return True
    explicit_flag = str(source.get("RATELIMIT_FAIL_CLOSED", "true")).strip().lower()
    if explicit_flag in {"0", "false", "no", "off"}:
        return False
    return True


class AppRateLimiter:
    """
    Per-Flask-application rate limiter wrapping Flask-Limiter and `limits`
    `MovingWindowRateLimiter` with fail-closed backend error handling.
    """

    def __init__(
        self,
        app: Flask,
        storage_uri: Optional[str] = None,
        storage_backend: Optional[Storage] = None,
    ):
        self.app = app
        self._explicit_storage_uri = storage_uri
        self._storage_override = storage_backend
        self._storage: Optional[Storage] = None
        self._bound_uri: Optional[str] = None
        self._strategy: Optional[MovingWindowRateLimiter] = None
        self._init_error: Optional[str] = None

        # Resolve initial URI for Flask-Limiter extension registration
        try:
            initial_uri = storage_uri or resolve_ratelimit_storage_uri()
        except Exception as exc:
            initial_uri = "memory://"
            self._init_error = str(exc)

        app.config.setdefault("RATELIMIT_STORAGE_URI", initial_uri)
        app.config.setdefault("RATELIMIT_IN_MEMORY_FALLBACK_ENABLED", False)
        app.config.setdefault("RATELIMIT_SWALLOW_ERRORS", False)
        app.config.setdefault("RATELIMIT_HEADERS_ENABLED", True)

        # Initialize Flask-Limiter on the Flask app with fallback disabled
        self.flask_limiter = Limiter(
            key_func=_flask_limiter_key_func,
            app=app,
            storage_uri=initial_uri if initial_uri not in _custom_storage_registry else "memory://",
            in_memory_fallback_enabled=False,
            swallow_errors=False,
            headers_enabled=True,
        )

    def _get_strategy_and_storage(self) -> Tuple[MovingWindowRateLimiter, Storage, str]:
        """Lazily initialize or refresh the storage backend for the active configuration."""
        if self._storage_override is not None:
            if self._strategy is None or self._storage is not self._storage_override:
                self._storage = self._storage_override
                self._strategy = MovingWindowRateLimiter(self._storage)
                if self._storage not in _active_test_storages:
                    _active_test_storages.append(self._storage)
            return self._strategy, self._storage, self._explicit_storage_uri or "custom://"

        target_uri = self._explicit_storage_uri or resolve_ratelimit_storage_uri()

        if self._strategy is not None and self._storage is not None and self._bound_uri == target_uri:
            return self._strategy, self._storage, target_uri

        if target_uri in _custom_storage_registry:
            storage = _custom_storage_registry[target_uri]
        elif target_uri.startswith(("redis://", "rediss://")) and "socket_connect_timeout" not in target_uri:
            timeout_sec = float(os.environ.get("RATELIMIT_SOCKET_TIMEOUT", "1.0"))
            storage = storage_from_string(
                target_uri,
                socket_connect_timeout=timeout_sec,
                socket_timeout=timeout_sec,
            )
        elif target_uri.startswith(("mongodb://", "mongodb+srv://")):
            # Store counters in the application database by default so Atlas users
            # scoped to DB_NAME (least privilege) can write them; override with
            # RATELIMIT_MONGO_DB. Short server-selection timeout keeps fail-closed fast.
            storage = storage_from_string(
                target_uri,
                database_name=(
                    os.environ.get("RATELIMIT_MONGO_DB")
                    or os.environ.get("DB_NAME")
                    or "student_db"
                ).strip(),
                counter_collection_name="ratelimit_counters",
                window_collection_name="ratelimit_windows",
                serverSelectionTimeoutMS=int(
                    float(os.environ.get("RATELIMIT_SOCKET_TIMEOUT", "2.0")) * 1000
                ),
            )
        else:
            storage = storage_from_string(target_uri)

        if storage not in _active_test_storages:
            _active_test_storages.append(storage)

        self._storage = storage
        self._bound_uri = target_uri
        self._strategy = MovingWindowRateLimiter(storage)
        return self._strategy, self._storage, target_uri

    def check_request(
        self, max_requests: int, window_seconds: int, scope: str
    ) -> Tuple[bool, int, dict[str, str], Optional[str]]:
        """
        Evaluate rate limit for the current request against the configured backend.

        Returns
        -------
        (allowed, retry_after_seconds, rate_headers, backend_error)
        """
        bucket_key, _ = build_rate_limit_key(scope)
        item = RateLimitItemPerSecond(int(max_requests), int(window_seconds))

        try:
            strategy, storage, resolved_uri = self._get_strategy_and_storage()
            if is_production_mode() and resolved_uri.lower().startswith("memory://"):
                raise RuntimeError(
                    "In-memory rate limit storage is forbidden in production."
                )

            allowed = bool(strategy.hit(item, bucket_key))
            stats = strategy.get_window_stats(item, bucket_key)
            now = time.time()
            reset_epoch = max(int(now) + 1, int(getattr(stats, "reset_time", now + window_seconds)))
            remaining = max(0, int(getattr(stats, "remaining", 0)))
            retry_after = max(1, int(reset_epoch - now)) if not allowed else 0

            headers = {
                "X-RateLimit-Limit": str(max_requests),
                "X-RateLimit-Remaining": str(remaining if allowed else 0),
                "X-RateLimit-Reset": str(reset_epoch),
            }
            if not allowed:
                headers["Retry-After"] = str(retry_after)

            return allowed, retry_after, headers, None

        except Exception as exc:
            logger.error(f"Rate limit storage error on scope '{scope}': {exc}")
            return False, 0, {}, str(exc)

    def reset(self) -> None:
        """Reset rate-limit counters in the bound storage (used by test suites)."""
        if self._storage is not None and hasattr(self._storage, "reset"):
            try:
                self._storage.reset()
            except Exception:
                pass


def init_app_rate_limiter(
    app: Flask,
    storage_uri: Optional[str] = None,
    storage_backend: Optional[Storage] = None,
) -> AppRateLimiter:
    """Attach an independent `AppRateLimiter` instance to the given Flask app."""
    limiter = AppRateLimiter(
        app, storage_uri=storage_uri, storage_backend=storage_backend
    )
    app.extensions["studentdb_rate_limiter"] = limiter
    return limiter


def clear_rate_limits(app: Optional[Flask] = None) -> None:
    """Reset rate limit counters across test storages and the given app instance."""
    if app is not None:
        ext = app.extensions.get("studentdb_rate_limiter")
        if ext is not None:
            ext.reset()

    for store in list(_active_test_storages):
        if hasattr(store, "reset"):
            try:
                store.reset()
            except Exception:
                pass


def rate_limit(max_requests: int = 60, window_seconds: int = 60, scope: str = "api") -> Callable:
    """
    Flask route decorator enforcing shared rate limiting via the current app's
    configured `AppRateLimiter` backend.
    """
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any):
            limiter: Optional[AppRateLimiter] = current_app.extensions.get(
                "studentdb_rate_limiter"
            )
            if limiter is None:
                limiter = init_app_rate_limiter(current_app)

            client_ip = extract_client_ip()
            allowed, retry_after, rl_headers, backend_error = limiter.check_request(
                max_requests=max_requests,
                window_seconds=window_seconds,
                scope=scope,
            )

            if backend_error is not None:
                if should_fail_closed():
                    log_audit_event(
                        "RATE_LIMIT_BACKEND_UNAVAILABLE",
                        getattr(g, "current_user", {}).get("username", "anonymous")
                        if getattr(g, "current_user", None)
                        else "anonymous",
                        getattr(g, "current_user", {}).get("role", "unauthenticated")
                        if getattr(g, "current_user", None)
                        else "unauthenticated",
                        f"Rejected request on scope '{scope}' due to unavailable rate-limit storage (fail-closed policy)",
                        status="warning",
                        ip_address=client_ip,
                    )
                    return make_response(
                        jsonify({
                            "success": False,
                            "message": "Rate limiting service unavailable. Request rejected by fail-closed security policy.",
                            "error": "Rate limiting service unavailable. Request rejected by fail-closed security policy.",
                        }),
                        503,
                    )

            if not allowed and backend_error is None:
                log_audit_event(
                    "RATE_LIMIT_EXCEEDED",
                    getattr(g, "current_user", {}).get("username", "anonymous")
                    if getattr(g, "current_user", None)
                    else "anonymous",
                    getattr(g, "current_user", {}).get("role", "unauthenticated")
                    if getattr(g, "current_user", None)
                    else "unauthenticated",
                    f"Rate limit exceeded on scope '{scope}'",
                    status="warning",
                    ip_address=client_ip,
                )
                resp = make_response(
                    jsonify({
                        "success": False,
                        "message": "Too many requests. Please try again later.",
                        "error": "Too many requests. Please try again later.",
                    }),
                    429,
                )
                for h_key, h_val in rl_headers.items():
                    resp.headers[h_key] = h_val
                return resp

            response = make_response(fn(*args, **kwargs))
            for h_key, h_val in rl_headers.items():
                response.headers.setdefault(h_key, h_val)
            return response

        return wrapper
    return decorator
