import logging
import os
import re
import sys

os.makedirs("logs", exist_ok=True)

_SENSITIVE_PATTERNS = [
    # 1. MongoDB and Redis URI credentials: mongodb+srv://user:pass@cluster or redis://:pass@host
    (
        re.compile(
            r"((?:mongodb(?:\+srv)?|rediss?)://[^:\s/@]*:)([^@\s]+)(@)",
            re.IGNORECASE,
        ),
        r"\1[REDACTED]\3",
    ),
    # 2. Authorization Bearer / Basic headers
    (
        re.compile(
            r"(Authorization\s*[:=]\s*(?:Bearer|Basic)\s+)[^\s,;'\"]+",
            re.IGNORECASE,
        ),
        r"\1[REDACTED]",
    ),
    (
        re.compile(r"(\bBearer\s+)[A-Za-z0-9._\-]+", re.IGNORECASE),
        r"\1[REDACTED]",
    ),
    # 3. JSON / dict quoted or unquoted key-value pairs for secrets, passwords, tokens, api keys
    (
        re.compile(
            r"(['\"]?(?:password|passwd|new_password|current_password|secret|secret_key|secret_key_previous|api_key|csrf_token|session_token|studentdb_session|x-csrf-token|ratelimit_storage_uri|redis_url)['\"]?\s*[:=]\s*['\"]?)([^'\"\s,;}]+)",
            re.IGNORECASE,
        ),
        r"\1[REDACTED]",
    ),
    # 4. Standalone Google Gemini (AIza...) and OpenAI (sk-...) API key patterns
    (
        re.compile(r"\bAIza[0-9A-Za-z\-_]{20,}\b"),
        "[REDACTED]",
    ),
    (
        re.compile(r"\bsk-[0-9A-Za-z\-_]{20,}\b"),
        "[REDACTED]",
    ),
]


def redact_sensitive_text(message):
    """Redact credentials, session tokens, API keys, and passwords from log strings."""
    if not message:
        return ""
    text = str(message)
    for pattern, replacement in _SENSITIVE_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


class RedactingFilter(logging.Filter):
    """Logging filter that scrubs sensitive secrets before emitting records."""

    def filter(self, record):
        if isinstance(record.msg, str):
            record.msg = redact_sensitive_text(record.msg)
        if record.args:
            record.args = tuple(
                redact_sensitive_text(a) if isinstance(a, str) else a
                for a in record.args
            )
        return True


logger = logging.getLogger("studentdb")
logger.setLevel(logging.INFO)

if not logger.handlers:
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s"
    )
    redacting_filter = RedactingFilter()

    file_handler = logging.FileHandler("logs/app.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.addFilter(redacting_filter)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    stream_handler.addFilter(redacting_filter)
    logger.addHandler(stream_handler)

logger.propagate = False
