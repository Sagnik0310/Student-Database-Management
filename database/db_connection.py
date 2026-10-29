import atexit
import os
import threading
from pymongo import MongoClient, ASCENDING
from dotenv import load_dotenv
from logs.logger import logger

# Load environment variables from config.env or .env
_config_path = os.path.join(os.path.dirname(__file__), "../config.env")
if os.path.exists(_config_path):
    load_dotenv(_config_path)
else:
    load_dotenv()

_client_lock = threading.Lock()
_cached_client = None
_cached_client_key = None
_indexes_initialized_for = set()


def ensure_indexes(db):
    """Ensure indexes exist idempotently across students, users, courses, enrollments, attendance, grades, and revoked_sessions collections."""
    if db is None:
        return
    try:
        # 1. Students collection indexes
        students = db["students"]
        students.create_index([("reg_no", ASCENDING)], unique=True, background=True)
        students.create_index([("branch", ASCENDING)], background=True)
        students.create_index([("name", ASCENDING)], background=True)
        students.create_index([("roll_no", ASCENDING)], background=True)

        # 2. Users & Session Revocation indexes
        users = db["users"]
        users.create_index([("username", ASCENDING)], unique=True, background=True)

        revoked_sessions = db["revoked_sessions"]
        revoked_sessions.create_index([("jti", ASCENDING)], unique=True, background=True)
        revoked_sessions.create_index(
            [("expires_at", ASCENDING)],
            expireAfterSeconds=0,
            background=True,
        )

        # 3. Courses collection indexes
        courses = db["courses"]
        courses.create_index([("course_code", ASCENDING)], unique=True, background=True)
        courses.create_index([("branch", ASCENDING), ("semester", ASCENDING)], background=True)
        courses.create_index([("faculty_username", ASCENDING)], background=True)

        # 4. Enrollments collection indexes (prevent duplicate student-course-semester enrollment)
        enrollments = db["enrollments"]
        enrollments.create_index(
            [
                ("reg_no", ASCENDING),
                ("course_code", ASCENDING),
                ("semester", ASCENDING),
                ("academic_year", ASCENDING),
            ],
            unique=True,
            background=True,
        )
        enrollments.create_index([("course_code", ASCENDING)], background=True)

        # 5. Attendance collection indexes (prevent duplicate student-course-date-session entry)
        attendance = db["attendance"]
        attendance.create_index(
            [
                ("reg_no", ASCENDING),
                ("course_code", ASCENDING),
                ("date", ASCENDING),
                ("session", ASCENDING),
            ],
            unique=True,
            background=True,
        )
        attendance.create_index([("course_code", ASCENDING), ("date", ASCENDING)], background=True)

        # 6. Grades collection indexes (prevent duplicate assessment entry for student-course-term)
        grades = db["grades"]
        grades.create_index(
            [
                ("reg_no", ASCENDING),
                ("course_code", ASCENDING),
                ("assessment_type", ASCENDING),
                ("semester", ASCENDING),
                ("academic_year", ASCENDING),
            ],
            unique=True,
            background=True,
        )
        grades.create_index([("course_code", ASCENDING)], background=True)
    except Exception as exc:
        logger.warning(f"Could not create MongoDB indexes (non-fatal): {exc}")


def get_connection():
    """Establish or reuse a pooled MongoDB database connection with safe timeouts."""
    global _cached_client, _cached_client_key

    mongo_uri = os.getenv("MONGO_URI")
    db_name = os.getenv("DB_NAME")

    if not mongo_uri or not db_name:
        logger.warning("MONGO_URI or DB_NAME is not configured.")
        return None

    key = (mongo_uri, db_name)
    with _client_lock:
        try:
            if _cached_client is None or _cached_client_key != key:
                if _cached_client is not None:
                    try:
                        _cached_client.close()
                    except Exception:
                        pass
                _cached_client = MongoClient(
                    mongo_uri,
                    serverSelectionTimeoutMS=5000,
                    connectTimeoutMS=5000,
                    socketTimeoutMS=10000,
                    maxPoolSize=50,
                    retryWrites=True,
                )
                _cached_client_key = key

            # Verify connection with a lightweight ping
            _cached_client.admin.command("ping")
            db = _cached_client[db_name]
            if key not in _indexes_initialized_for:
                ensure_indexes(db)
                _indexes_initialized_for.add(key)
                logger.info("MongoDB connected and indexes verified successfully")
            return db

        except Exception as e:
            logger.error(f"MongoDB connection error: {e}")
            return None


def check_db_readiness():
    """
    Perform a lightweight readiness check for health probes.
    Never exposes raw connection strings, hostnames, or internal stack traces.
    """
    if os.environ.get("STUDENTDB_TEST_MODE") == "1":
        return {
            "ready": True,
            "status": "ready",
            "database": "connected",
            "mode": "test_memory",
        }

    db = get_connection()
    if db is None:
        return {
            "ready": False,
            "status": "unavailable",
            "database": "disconnected",
            "mode": "mongodb",
        }

    return {
        "ready": True,
        "status": "ready",
        "database": "connected",
        "mode": "mongodb",
    }


def close_connection():
    """Safely close the pooled MongoDB client on process shutdown."""
    global _cached_client, _cached_client_key
    with _client_lock:
        if _cached_client is not None:
            try:
                _cached_client.close()
                logger.info("MongoDB connection pool closed cleanly")
            except Exception:
                pass
            finally:
                _cached_client = None
                _cached_client_key = None
                _indexes_initialized_for.clear()


atexit.register(close_connection)
