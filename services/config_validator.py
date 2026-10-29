"""
Centralized environment and runtime configuration validation for
Student Database Management System 2.0 (Phase 5).

Fails fast in production mode when required environment variables are missing,
placeholder values are left in place, or insecure cookie/CORS combinations are
configured. Never logs or prints secret values.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Mapping, Optional

from logs.logger import logger


class ConfigValidationError(RuntimeError):
    """Raised when runtime configuration fails production validation checks."""

    def __init__(self, errors: List[str]):
        self.errors = list(errors)
        super().__init__(
            "Invalid application configuration: " + "; ".join(self.errors)
        )


KNOWN_SECRET_PLACEHOLDERS = {
    "",
    "changeme",
    "secret",
    "dev",
    "development",
    "default",
    "password",
    "replace-with-a-64-char-random-cryptographic-secret",
    "replace-with-your-provider-api-key",
    "your-secret-key",
    "studentdb-dev-only-secret-key-do-not-use-in-prod",
}

KNOWN_WEAK_DEMO_PASSWORDS = {
    "Admin@123",
    "Faculty@123",
    "Student@123",
    "password",
    "12345678",
    "admin123",
}

ALLOWED_SAMESITE_VALUES = {"lax", "strict", "none"}
ALLOWED_AI_PROVIDERS = {"deterministic", "gemini", "openai"}


def is_production_mode(env: Optional[Mapping[str, str]] = None) -> bool:
    """
    Determine whether the process is running in production mode.
    Explicit test mode (`STUDENTDB_TEST_MODE=1`) overrides production detection
    unless `strict_production` is explicitly requested by the caller.
    """
    source = env if env is not None else os.environ
    if str(source.get("STUDENTDB_TEST_MODE", "")).strip() == "1":
        return False

    app_env = str(
        source.get("APP_ENV")
        or source.get("FLASK_ENV")
        or source.get("ENVIRONMENT")
        or "development"
    ).strip().lower()
    render_flag = str(source.get("RENDER", "")).strip().lower() == "true"
    return app_env in {"production", "prod"} or render_flag


def _parse_bool(value: Optional[str], default: bool = False) -> bool:
    if value is None or str(value).strip() == "":
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def validate_environment_config(
    env: Optional[Mapping[str, str]] = None,
    strict_production: Optional[bool] = None,
    raise_on_error: bool = True,
) -> Dict[str, Any]:
    """
    Validate runtime environment variables for security and deployment readiness.

    Parameters
    ----------
    env : Mapping[str, str], optional
        Environment mapping to inspect (defaults to `os.environ`).
    strict_production : bool, optional
        Force production validation rules regardless of `STUDENTDB_TEST_MODE`.
    raise_on_error : bool
        When True (default), raises `ConfigValidationError` if any errors exist.

    Returns
    -------
    dict
        Sanitized summary containing `environment`, `production`, `valid`,
        `errors`, and `warnings` (never includes raw secrets or credentials).
    """
    source = env if env is not None else os.environ
    prod = (
        bool(strict_production)
        if strict_production is not None
        else is_production_mode(source)
    )

    errors: List[str] = []
    warnings: List[str] = []

    # 1. Database settings
    mongo_uri = str(source.get("MONGO_URI", "")).strip()
    db_name = str(source.get("DB_NAME", "student_db")).strip()

    if prod:
        if not mongo_uri:
            errors.append("MONGO_URI is required in production.")
        elif not (
            mongo_uri.startswith("mongodb://")
            or mongo_uri.startswith("mongodb+srv://")
        ):
            errors.append(
                "MONGO_URI must start with 'mongodb://' or 'mongodb+srv://'."
            )
        elif "<username>" in mongo_uri or "<password>" in mongo_uri:
            errors.append(
                "MONGO_URI contains unreplaced placeholder credentials."
            )

        if not db_name:
            errors.append("DB_NAME must not be empty in production.")
    else:
        if mongo_uri and not (
            mongo_uri.startswith("mongodb://")
            or mongo_uri.startswith("mongodb+srv://")
        ):
            errors.append(
                "MONGO_URI must start with 'mongodb://' or 'mongodb+srv://'."
            )

    # 2. Cryptographic session secret validation
    secret_key = str(
        source.get("SECRET_KEY") or source.get("JWT_SECRET_KEY") or ""
    ).strip()
    secret_key_prev = str(source.get("SECRET_KEY_PREVIOUS", "")).strip()

    if prod:
        if not secret_key:
            errors.append("SECRET_KEY is required in production.")
        elif secret_key.lower() in KNOWN_SECRET_PLACEHOLDERS:
            errors.append(
                "SECRET_KEY matches a forbidden placeholder or default value."
            )
        elif len(secret_key) < 32:
            errors.append(
                "SECRET_KEY must be at least 32 characters long in production."
            )

        if secret_key_prev:
            if secret_key_prev.lower() in KNOWN_SECRET_PLACEHOLDERS:
                errors.append(
                    "SECRET_KEY_PREVIOUS matches a forbidden placeholder value."
                )
            elif len(secret_key_prev) < 32:
                errors.append(
                    "SECRET_KEY_PREVIOUS must be at least 32 characters long when set in production."
                )
    else:
        if not secret_key:
            warnings.append(
                "SECRET_KEY is not set; using ephemeral development fallback."
            )

    # 3. Session TTL validation
    raw_ttl = str(source.get("SESSION_TTL_SECONDS", "28800")).strip()
    try:
        ttl_val = int(raw_ttl)
        if ttl_val < 60 or ttl_val > 604800:
            errors.append(
                "SESSION_TTL_SECONDS must be between 60 and 604800 seconds."
            )
    except ValueError:
        errors.append("SESSION_TTL_SECONDS must be a valid integer.")

    # 4. Cookie security validation
    samesite_raw = str(source.get("COOKIE_SAMESITE", "Lax")).strip()
    if samesite_raw.lower() not in ALLOWED_SAMESITE_VALUES:
        errors.append(
            "COOKIE_SAMESITE must be one of: Lax, Strict, None."
        )
    cookie_secure = _parse_bool(
        source.get("COOKIE_SECURE"), default=prod
    )
    if prod and not cookie_secure:
        errors.append("COOKIE_SECURE must be true in production.")
    if samesite_raw.lower() == "none" and not cookie_secure:
        errors.append(
            "COOKIE_SECURE must be true when COOKIE_SAMESITE is set to 'None'."
        )

    # 5. CORS origins validation
    cors_raw = str(source.get("CORS_ORIGINS", "")).strip()
    origins = [o.strip() for o in cors_raw.split(",") if o.strip()]
    if prod:
        if not origins:
            errors.append(
                "CORS_ORIGINS must specify at least one explicit origin in production."
            )
        for origin in origins:
            if origin == "*":
                errors.append(
                    "Wildcard '*' in CORS_ORIGINS is forbidden when credentialed cookies are enabled."
                )
            elif not origin.startswith("https://"):
                errors.append(
                    f"CORS origin '{origin}' must use https:// in production (credentialed cookies require secure origins)."
                )
            elif origin.endswith("/"):
                errors.append(
                    f"CORS origin '{origin}' must not include a trailing slash (browsers send the Origin header without one)."
                )
    else:
        for origin in origins:
            if origin == "*":
                errors.append(
                    "Wildcard '*' in CORS_ORIGINS is forbidden when credentialed cookies are enabled."
                )

    # 6. Bootstrap account credential checks in production
    # Accept both the documented names (ADMIN_PASSWORD, ...) and legacy DEFAULT_* aliases.
    allow_demo_users = _parse_bool(
        source.get("ALLOW_DEFAULT_DEMO_USERS"), default=not prod
    )
    if prod:
        bootstrap_pairs = (
            ("ADMIN_PASSWORD", "DEFAULT_ADMIN_PASSWORD"),
            ("FACULTY_PASSWORD", "DEFAULT_FACULTY_PASSWORD"),
            ("STUDENT_PASSWORD", "DEFAULT_STUDENT_PASSWORD"),
        )
        for primary, legacy in bootstrap_pairs:
            val = str(source.get(primary) or source.get(legacy) or "").strip()
            if val and val in KNOWN_WEAK_DEMO_PASSWORDS:
                errors.append(
                    f"{primary} uses a known default demo password in production."
                )
            elif val and len(val) < 12:
                errors.append(
                    f"{primary} must be at least 12 characters long in production."
                )
        admin_val = str(
            source.get("ADMIN_PASSWORD") or source.get("DEFAULT_ADMIN_PASSWORD") or ""
        ).strip()
        if not admin_val:
            warnings.append(
                "ADMIN_PASSWORD is not set; no Admin account will be auto-created. "
                "Ensure an Admin user already exists in the users collection."
            )
        if allow_demo_users:
            warnings.append(
                "ALLOW_DEFAULT_DEMO_USERS=true in production; Faculty/Student demo accounts "
                "will be created only if strong FACULTY_PASSWORD/STUDENT_PASSWORD are set."
            )

    # 7. AI Assistant provider & key validation
    ai_provider = (
        str(source.get("AI_ASSISTANT_PROVIDER", "deterministic"))
        .strip()
        .lower()
        or "deterministic"
    )
    if ai_provider not in ALLOWED_AI_PROVIDERS:
        errors.append(
            "AI_ASSISTANT_PROVIDER must be one of: deterministic, gemini, openai."
        )
    else:
        ai_key = str(
            source.get("AI_ASSISTANT_API_KEY")
            or source.get("GEMINI_API_KEY")
            or source.get("OPENAI_API_KEY")
            or ""
        ).strip()
        if ai_provider in {"gemini", "openai"}:
            if not ai_key or ai_key.lower() in KNOWN_SECRET_PLACEHOLDERS:
                if prod:
                    errors.append(
                        f"AI_ASSISTANT_API_KEY is required when AI_ASSISTANT_PROVIDER='{ai_provider}' in production."
                    )
                else:
                    warnings.append(
                        f"AI_ASSISTANT_PROVIDER='{ai_provider}' configured without API key; assistant will fall back to deterministic mode."
                    )

    # 8. Shared Rate-Limiting Storage validation
    ratelimit_uri = str(
        source.get("RATELIMIT_STORAGE_URI") or source.get("REDIS_URL") or ""
    ).strip()
    if prod:
        if ratelimit_uri:
            if ratelimit_uri.lower().startswith("memory://"):
                errors.append(
                    "RATELIMIT_STORAGE_URI cannot use process-local 'memory://' in production; configure a shared Redis ('redis://', 'rediss://') or MongoDB ('mongodb://', 'mongodb+srv://') backend."
                )
            elif not ratelimit_uri.startswith(
                ("redis://", "rediss://", "mongodb://", "mongodb+srv://")
            ):
                errors.append(
                    "RATELIMIT_STORAGE_URI must start with 'redis://', 'rediss://', 'mongodb://', or 'mongodb+srv://' in production."
                )
            elif "<username>" in ratelimit_uri or "<password>" in ratelimit_uri:
                errors.append(
                    "RATELIMIT_STORAGE_URI contains unreplaced placeholder credentials."
                )
        else:
            if not (
                mongo_uri.startswith("mongodb://")
                or mongo_uri.startswith("mongodb+srv://")
            ):
                errors.append(
                    "A shared rate-limit backend (RATELIMIT_STORAGE_URI or MONGO_URI) is required in production."
                )
            else:
                warnings.append(
                    "RATELIMIT_STORAGE_URI not explicitly set; defaulting shared rate limiting to MONGO_URI."
                )
    else:
        if ratelimit_uri and not ratelimit_uri.startswith(
            ("redis://", "rediss://", "mongodb://", "mongodb+srv://", "memory://")
        ):
            errors.append(
                "RATELIMIT_STORAGE_URI must use a valid scheme (redis://, rediss://, mongodb://, mongodb+srv://, or memory://)."
            )

    result = {
        "environment": "production" if prod else "development",
        "production": prod,
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "ai_provider": ai_provider,
        "cookie_samesite": samesite_raw.capitalize()
        if samesite_raw.lower() in {"lax", "strict"}
        else ("None" if samesite_raw.lower() == "none" else samesite_raw),
        "cookie_secure": cookie_secure,
    }

    for warning in warnings:
        logger.warning(f"Config validation warning: {warning}")

    if errors:
        logger.error(
            f"Config validation failed ({len(errors)} issue(s)): {'; '.join(errors)}"
        )
        if raise_on_error:
            raise ConfigValidationError(errors)

    return result

