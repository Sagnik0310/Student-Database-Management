import os
import re
from datetime import datetime, timezone
from database.db_connection import get_connection
from models.student import Student
from logs.logger import logger


class _InMemoryCursor:
    def __init__(self, docs):
        self._docs = list(docs)

    def sort(self, key, direction=1):
        reverse = direction == -1
        self._docs.sort(
            key=lambda d: (d.get(key) is None, d.get(key, "")),
            reverse=reverse,
        )
        return self

    def __iter__(self):
        return iter(self._docs)


class _WriteResult:
    def __init__(self, matched_count=0, deleted_count=0):
        self.matched_count = matched_count
        self.deleted_count = deleted_count


class _InMemoryStudentsCollection:
    """Isolated in-memory collection used when STUDENTDB_TEST_MODE=1."""

    def __init__(self):
        self._store = {}

    def clear(self):
        self._store.clear()

    def find_one(self, query):
        reg_no = query.get("reg_no")
        if reg_no is not None:
            doc = self._store.get(reg_no)
            return dict(doc) if doc else None
        for doc in self._store.values():
            if all(doc.get(k) == v for k, v in query.items()):
                return dict(doc)
        return None

    def insert_one(self, doc):
        self._store[doc["reg_no"]] = dict(doc)
        return _WriteResult(matched_count=1)

    def update_one(self, filter_q, update_q):
        reg_no = filter_q.get("reg_no")
        if reg_no not in self._store:
            return _WriteResult(matched_count=0)
        set_fields = update_q.get("$set", {})
        self._store[reg_no].update(set_fields)
        return _WriteResult(matched_count=1)

    def delete_one(self, filter_q):
        reg_no = filter_q.get("reg_no")
        if reg_no in self._store:
            del self._store[reg_no]
            return _WriteResult(deleted_count=1)
        return _WriteResult(deleted_count=0)

    def delete_many(self, filter_q):
        target_list = filter_q.get("reg_no", {}).get("$in", [])
        deleted = 0
        for reg_no in target_list:
            if reg_no in self._store:
                del self._store[reg_no]
                deleted += 1
        return _WriteResult(deleted_count=deleted)

    def find(self, query=None):
        query = query or {}
        results = []
        for doc in self._store.values():
            if self._matches(doc, query):
                results.append(dict(doc))
        return _InMemoryCursor(results)

    def _matches(self, doc, query):
        for k, v in query.items():
            if k == "$or":
                if not any(self._matches(doc, sub) for sub in v):
                    return False
            elif k == "$and":
                if not all(self._matches(doc, sub) for sub in v):
                    return False
            elif isinstance(v, dict) and "$regex" in v:
                flags = re.IGNORECASE if "i" in v.get("$options", "") else 0
                val_str = str(doc.get(k, "") or "")
                if not re.search(v["$regex"], val_str, flags):
                    return False
            elif isinstance(v, dict) and "$exists" in v:
                exists = k in doc and doc[k] is not None
                if exists != bool(v["$exists"]):
                    return False
            else:
                if doc.get(k) != v:
                    return False
        return True


_test_students_collection = _InMemoryStudentsCollection()

if os.environ.get("STUDENTDB_TEST_MODE") == "1":
    db = None
    students_collection = _test_students_collection
else:
    db = get_connection()
    if db is None:
        print("Database connection failed. App will still run.")
        students_collection = None
    else:
        students_collection = db["students"]


def reset_test_students():
    """Reset the isolated in-memory test student store."""
    _test_students_collection.clear()


def _get_collection():
    """Return active students collection or isolated test collection in test mode."""
    global db, students_collection
    if os.environ.get("STUDENTDB_TEST_MODE") == "1":
        return _test_students_collection
    if students_collection is not None:
        return students_collection
    db = get_connection()
    if db is not None:
        students_collection = db["students"]
    return students_collection


EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _validate_optional_fields(extra):
    """Validate optional extended fields if provided."""
    email = str(extra.get("email", "") or "").strip()
    if email and not EMAIL_REGEX.match(email):
        return "Invalid email address format"

    gpa = extra.get("gpa")
    if gpa not in (None, ""):
        try:
            gpa_val = float(gpa)
            if gpa_val < 0 or gpa_val > 10:
                return "GPA must be between 0.0 and 10.0"
        except (ValueError, TypeError):
            return "GPA must be a valid number"

    attendance = extra.get("attendance_pct")
    if attendance not in (None, ""):
        try:
            att_val = float(attendance)
            if att_val < 0 or att_val > 100:
                return "Attendance percentage must be between 0 and 100"
        except (ValueError, TypeError):
            return "Attendance percentage must be a valid number"

    return None


def add_student(reg_no, roll_no, name, age, branch, **extra_fields):
    collection = _get_collection()
    if collection is None:
        return {"error": "Database not connected"}

    reg_no = str(reg_no or "").strip()
    roll_no = str(roll_no or "").strip()
    name = str(name or "").strip()
    branch = str(branch or "").strip()

    if not reg_no:
        return {"error": "Registration number cannot be empty"}

    if not roll_no:
        return {"error": "Roll number cannot be empty"}

    if not name:
        return {"error": "Name cannot be empty"}

    try:
        age = int(age)
    except (ValueError, TypeError):
        return {"error": "Age must be a valid integer"}

    if age <= 0 or age > 120:
        return {"error": "Age must be greater than 0"}

    if not branch:
        return {"error": "Branch cannot be empty"}

    if not re.match(r"^[A-Za-z0-9]+$", reg_no):
        return {"error": "Registration number must be alphanumeric"}

    opt_error = _validate_optional_fields(extra_fields)
    if opt_error:
        return {"error": opt_error}

    existing_student = collection.find_one({"reg_no": reg_no})
    if existing_student:
        return {"error": "Student already exists"}

    student_obj = Student(
        reg_no=reg_no,
        roll_no=roll_no,
        name=name,
        age=age,
        branch=branch,
        email=extra_fields.get("email", ""),
        phone=extra_fields.get("phone", ""),
        semester=extra_fields.get("semester", ""),
        academic_year=extra_fields.get("academic_year", ""),
        admission_date=extra_fields.get("admission_date", ""),
        status=extra_fields.get("status", "Active"),
        gpa=extra_fields.get("gpa"),
        attendance_pct=extra_fields.get("attendance_pct"),
    )

    try:
        collection.insert_one(student_obj.to_dict())
        logger.info(f"Student added: reg_no={reg_no}")
        return {
            "success": True,
            "message": "Student added successfully",
            "student": student_obj.to_dict(),
        }
    except Exception as e:
        logger.error(f"Error adding student {reg_no}: {e}")
        return {"error": "Failed to add student record"}


def view_students(
    search=None,
    branch=None,
    status=None,
    semester=None,
    sort_by=None,
    order="asc",
):
    collection = _get_collection()
    if collection is None:
        return []

    try:
        query = {}

        if search and str(search).strip():
            escaped = re.escape(str(search).strip())
            regex = {"$regex": escaped, "$options": "i"}
            query["$or"] = [
                {"reg_no": regex},
                {"roll_no": regex},
                {"name": regex},
                {"branch": regex},
                {"email": regex},
            ]

        if branch and str(branch).strip() and str(branch).strip().lower() != "all":
            query["branch"] = str(branch).strip()

        if status and str(status).strip() and str(status).strip().lower() != "all":
            status_val = str(status).strip()
            if status_val == "Active":
                query["$and"] = query.get("$and", []) + [
                    {
                        "$or": [
                            {"status": "Active"},
                            {"status": {"$exists": False}},
                            {"status": ""},
                        ]
                    }
                ]
            else:
                query["status"] = status_val

        if semester and str(semester).strip() and str(semester).strip().lower() != "all":
            query["semester"] = str(semester).strip()

        cursor = collection.find(query)

        allowed_sort_fields = {
            "reg_no",
            "roll_no",
            "name",
            "age",
            "branch",
            "gpa",
            "attendance_pct",
            "created_at",
        }
        if sort_by in allowed_sort_fields:
            direction = -1 if str(order).lower() == "desc" else 1
            cursor = cursor.sort(sort_by, direction)

        students = []
        for doc in cursor:
            student_obj = Student.from_dict(doc)
            if student_obj:
                students.append(student_obj.to_dict())

        return students

    except Exception as e:
        logger.error(f"Error fetching students: {e}")
        return []


def search_student(reg_no):
    collection = _get_collection()
    if collection is None:
        return None

    try:
        reg_no = str(reg_no or "").strip()
        if not reg_no:
            return None

        doc = collection.find_one({"reg_no": reg_no})
        if not doc:
            return None

        return Student.from_dict(doc).to_dict()

    except Exception as e:
        logger.error(f"Error searching student {reg_no}: {e}")
        return None


def update_student(reg_no, name, age, branch, **extra_fields):
    collection = _get_collection()
    if collection is None:
        return {"error": "Database not connected"}

    reg_no = str(reg_no or "").strip()
    name = str(name or "").strip()
    branch = str(branch or "").strip()

    if not reg_no:
        return {"error": "Registration number cannot be empty"}

    if not name:
        return {"error": "Name cannot be empty"}

    try:
        age = int(age)
    except (ValueError, TypeError):
        return {"error": "Age must be a valid integer"}

    if age <= 0 or age > 120:
        return {"error": "Age must be greater than 0"}

    if not branch:
        return {"error": "Branch cannot be empty"}

    opt_error = _validate_optional_fields(extra_fields)
    if opt_error:
        return {"error": opt_error}

    try:
        set_fields = {
            "name": name,
            "age": age,
            "branch": branch,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        if "roll_no" in extra_fields and str(extra_fields["roll_no"] or "").strip():
            set_fields["roll_no"] = str(extra_fields["roll_no"]).strip()

        for opt_key in (
            "email",
            "phone",
            "semester",
            "academic_year",
            "admission_date",
            "status",
        ):
            if opt_key in extra_fields and extra_fields[opt_key] is not None:
                set_fields[opt_key] = str(extra_fields[opt_key]).strip()

        if "gpa" in extra_fields:
            gpa_raw = extra_fields["gpa"]
            set_fields["gpa"] = float(gpa_raw) if gpa_raw not in (None, "") else None

        if "attendance_pct" in extra_fields:
            att_raw = extra_fields["attendance_pct"]
            set_fields["attendance_pct"] = (
                float(att_raw) if att_raw not in (None, "") else None
            )

        result = collection.update_one(
            {"reg_no": reg_no},
            {"$set": set_fields},
        )

        if result.matched_count == 0:
            return {"error": "Student not found"}

        logger.info(f"Student updated: reg_no={reg_no}")
        return {"success": True, "message": "Student updated successfully"}

    except Exception as e:
        logger.error(f"Error updating student {reg_no}: {e}")
        return {"error": "Failed to update student"}


def delete_student(reg_no):
    collection = _get_collection()
    if collection is None:
        return {"error": "Database not connected"}

    reg_no = str(reg_no or "").strip()
    if not reg_no:
        return {"error": "Registration number cannot be empty"}

    try:
        result = collection.delete_one({"reg_no": reg_no})

        if result.deleted_count == 0:
            return {"error": "Student not found"}

        logger.info(f"Student deleted: reg_no={reg_no}")
        return {"success": True, "message": "Student deleted successfully"}

    except Exception as e:
        logger.error(f"Error deleting student {reg_no}: {e}")
        return {"error": "Failed to delete student"}


def bulk_delete_students(reg_nos):
    """Delete multiple student records by registration number list."""
    collection = _get_collection()
    if collection is None:
        return {"error": "Database not connected"}

    if not isinstance(reg_nos, list) or not reg_nos:
        return {"error": "A non-empty list of registration numbers is required"}

    clean_ids = [str(r).strip() for r in reg_nos if str(r).strip()]
    if not clean_ids:
        return {"error": "No valid registration numbers provided"}

    try:
        result = collection.delete_many({"reg_no": {"$in": clean_ids}})
        logger.info(f"Bulk deleted {result.deleted_count} students")
        return {
            "success": True,
            "deleted_count": result.deleted_count,
            "message": f"Deleted {result.deleted_count} student(s) successfully",
        }
    except Exception as e:
        logger.error(f"Error in bulk delete: {e}")
        return {"error": "Bulk deletion failed"}


def get_student_analytics(students_subset=None):
    """Calculate real-time analytics from actual student records."""
    students = (
        students_subset if isinstance(students_subset, list) else view_students()
    )
    total = len(students)

    branch_counts = {}
    status_counts = {}
    semester_counts = {}
    ages = []
    gpas = []
    attendances = []

    for s in students:
        branch = s.get("branch") or "Unassigned"
        branch_counts[branch] = branch_counts.get(branch, 0) + 1

        status = s.get("status") or "Active"
        status_counts[status] = status_counts.get(status, 0) + 1

        sem = s.get("semester")
        if sem:
            semester_counts[str(sem)] = semester_counts.get(str(sem), 0) + 1

        if isinstance(s.get("age"), (int, float)) and s["age"] > 0:
            ages.append(s["age"])

        if s.get("gpa") is not None:
            try:
                gpas.append(float(s["gpa"]))
            except (ValueError, TypeError):
                pass

        if s.get("attendance_pct") is not None:
            try:
                attendances.append(float(s["attendance_pct"]))
            except (ValueError, TypeError):
                pass

    return {
        "total_students": total,
        "active_students": status_counts.get("Active", 0),
        "total_branches": len(branch_counts),
        "average_age": round(sum(ages) / len(ages), 1) if ages else 0,
        "average_gpa": round(sum(gpas) / len(gpas), 2) if gpas else None,
        "average_attendance": (
            round(sum(attendances) / len(attendances), 1) if attendances else None
        ),
        "branch_distribution": [
            {"branch": k, "count": v}
            for k, v in sorted(branch_counts.items(), key=lambda x: (-x[1], x[0]))
        ],
        "status_distribution": [
            {"status": k, "count": v}
            for k, v in sorted(status_counts.items(), key=lambda x: (-x[1], x[0]))
        ],
        "semester_distribution": [
            {"semester": f"Sem {k}", "count": v}
            for k, v in sorted(semester_counts.items(), key=lambda x: x[0])
        ],
    }
