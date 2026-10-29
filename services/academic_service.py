import os
import re
from datetime import datetime, timezone
from database.db_connection import get_connection
from models.academic import (
    DEFAULT_GRADING_SCALE,
    GradingScale,
    Course,
    Enrollment,
    AttendanceRecord,
    GradeRecord,
)
from services.student_service import search_student, update_student, view_students
from logs.logger import logger

COURSE_CODE_REGEX = re.compile(r"^[A-Za-z0-9_-]{2,20}$")
DATE_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# ==========================================
# IN-MEMORY STORES FOR TEST MODE / FALLBACK
# ==========================================
_mem_courses = {}
_mem_enrollments = {}
_mem_attendance = {}
_mem_grades = {}
_mem_grading_scale = dict(DEFAULT_GRADING_SCALE)


def reset_test_academics():
    """Reset in-memory academic collections for isolated unit/integration tests."""
    global _mem_grading_scale
    _mem_courses.clear()
    _mem_enrollments.clear()
    _mem_attendance.clear()
    _mem_grades.clear()
    _mem_grading_scale = dict(DEFAULT_GRADING_SCALE)


def _is_test_mode():
    return os.environ.get("STUDENTDB_TEST_MODE") == "1"


def _get_db():
    if _is_test_mode():
        return None
    return get_connection()


# ==========================================
# RBAC AUTHORIZATION HELPERS FOR ACADEMICS
# ==========================================
def can_manage_course(user, course_doc):
    """Return True if user is Admin or Faculty assigned to this course or its branch."""
    if not user or not course_doc:
        return False
    role = user.get("role")
    if role == "Admin":
        return True
    if role == "Faculty":
        uname = str(user.get("username") or "").strip()
        course_faculty = str(course_doc.get("faculty_username") or "").strip()
        if uname and course_faculty and uname == course_faculty:
            return True
        assigned_branches = [
            str(b).strip().upper() for b in (user.get("assigned_branches") or [])
        ]
        course_branch = str(course_doc.get("branch") or "").strip().upper()
        if "*" in assigned_branches or (course_branch and course_branch in assigned_branches):
            return True
    return False


# ==========================================
# 1. CONFIGURABLE GRADING SCALE
# ==========================================
def get_grading_scale():
    """Return the active GradingScale instance."""
    db = _get_db()
    if db is not None:
        try:
            doc = db["grading_config"].find_one({"config_id": "default"})
            if doc:
                return GradingScale(doc)
        except Exception:
            pass
    return GradingScale(_mem_grading_scale)


def update_grading_scale(new_config):
    """Validate and persist an updated grading scale configuration."""
    global _mem_grading_scale
    err = GradingScale.validate_config(new_config)
    if err:
        return {"error": err}

    scale = GradingScale(new_config)
    scale_dict = scale.to_dict()
    _mem_grading_scale = dict(scale_dict)

    db = _get_db()
    if db is not None:
        try:
            db["grading_config"].update_one(
                {"config_id": "default"},
                {"$set": {**scale_dict, "config_id": "default"}},
                upsert=True,
            )
        except Exception as exc:
            logger.error(f"Failed to persist grading config in MongoDB: {exc}")

    return {
        "success": True,
        "message": "Grading scale updated successfully",
        "grading_scale": scale_dict,
    }


# ==========================================
# 2. COURSE MANAGEMENT
# ==========================================
def get_course(course_code):
    code = str(course_code or "").strip().upper()
    if not code:
        return None
    db = _get_db()
    if db is not None:
        try:
            doc = db["courses"].find_one({"course_code": code})
            if doc:
                return Course.from_dict(doc).to_dict()
        except Exception:
            pass
    mem_doc = _mem_courses.get(code)
    return Course.from_dict(mem_doc).to_dict() if mem_doc else None


def _count_active_enrollments(course_code):
    code = str(course_code or "").strip().upper()
    db = _get_db()
    if db is not None:
        try:
            return db["enrollments"].count_documents(
                {"course_code": code, "status": "Enrolled"}
            )
        except Exception:
            pass
    return sum(
        1
        for e in _mem_enrollments.values()
        if e.get("course_code") == code and e.get("status") == "Enrolled"
    )


def create_course(
    course_code,
    course_name,
    branch,
    credits=3,
    semester="1",
    academic_year="2025-2026",
    faculty_username="",
    capacity=60,
    description="",
):
    code = str(course_code or "").strip().upper()
    name = str(course_name or "").strip()
    dept = str(branch or "").strip().upper()

    if not code or not COURSE_CODE_REGEX.match(code):
        return {
            "error": "Course code must be 2-20 alphanumeric characters (e.g., CS301)"
        }
    if not name:
        return {"error": "Course name cannot be empty"}
    if not dept:
        return {"error": "Branch / Department cannot be empty"}

    try:
        cred_val = float(credits)
        if cred_val <= 0 or cred_val > 20:
            return {"error": "Credits must be between 0.5 and 20"}
    except (ValueError, TypeError):
        return {"error": "Credits must be a valid number"}

    try:
        cap_val = int(capacity)
        if cap_val <= 0 or cap_val > 1000:
            return {"error": "Capacity must be between 1 and 1000"}
    except (ValueError, TypeError):
        return {"error": "Capacity must be a valid integer"}

    if get_course(code):
        return {"error": f"Course '{code}' already exists"}

    course_obj = Course(
        course_code=code,
        course_name=name,
        branch=dept,
        credits=cred_val,
        semester=str(semester or "1").strip(),
        academic_year=str(academic_year or "2025-2026").strip(),
        faculty_username=str(faculty_username or "").strip(),
        capacity=cap_val,
        status="Active",
        description=description,
    )
    course_dict = course_obj.to_dict()
    _mem_courses[code] = course_dict

    db = _get_db()
    if db is not None:
        try:
            db["courses"].insert_one(dict(course_dict))
        except Exception as exc:
            logger.error(f"Error inserting course {code}: {exc}")
            return {"error": "Failed to save course to database"}

    return {
        "success": True,
        "message": "Course created successfully",
        "course": {**course_dict, "enrolled_count": 0},
    }


def list_courses(
    user=None,
    branch=None,
    semester=None,
    status=None,
    include_archived=False,
):
    db = _get_db()
    raw_list = []
    if db is not None:
        try:
            for doc in db["courses"].find():
                c = Course.from_dict(doc)
                if c:
                    raw_list.append(c.to_dict())
        except Exception:
            raw_list = [Course.from_dict(d).to_dict() for d in _mem_courses.values()]
    else:
        raw_list = [Course.from_dict(d).to_dict() for d in _mem_courses.values()]

    results = []
    for c in raw_list:
        if not include_archived and not status and c.get("status") == "Archived":
            continue
        if status and status != "All" and c.get("status") != status:
            continue
        if branch and branch != "All" and c.get("branch") != str(branch).strip().upper():
            continue
        if semester and semester != "All" and str(c.get("semester")) != str(semester).strip():
            continue

        # Faculty only see courses they are permitted to manage
        if user and user.get("role") == "Faculty" and not can_manage_course(user, c):
            continue

        results.append({
            **c,
            "enrolled_count": _count_active_enrollments(c["course_code"]),
        })

    results.sort(key=lambda x: x["course_code"])
    return results


def update_course(course_code, **updates):
    code = str(course_code or "").strip().upper()
    existing = get_course(code)
    if not existing:
        return {"error": "Course not found"}

    if "credits" in updates and updates["credits"] is not None:
        try:
            cred = float(updates["credits"])
            if cred <= 0 or cred > 20:
                return {"error": "Credits must be between 0.5 and 20"}
            existing["credits"] = cred
        except (ValueError, TypeError):
            return {"error": "Credits must be a valid number"}

    if "capacity" in updates and updates["capacity"] is not None:
        try:
            cap = int(updates["capacity"])
            if cap <= 0 or cap > 1000:
                return {"error": "Capacity must be between 1 and 1000"}
            existing["capacity"] = cap
        except (ValueError, TypeError):
            return {"error": "Capacity must be a valid integer"}

    for field in (
        "course_name",
        "branch",
        "semester",
        "academic_year",
        "faculty_username",
        "status",
        "description",
    ):
        if field in updates and updates[field] is not None:
            val = str(updates[field]).strip()
            if field == "branch":
                val = val.upper()
            if field in ("course_name", "branch") and not val:
                return {"error": f"{field} cannot be empty"}
            if field == "status" and val not in Course.VALID_STATUSES:
                return {"error": "Invalid course status"}
            existing[field] = val

    existing["updated_at"] = datetime.now(timezone.utc).isoformat()
    _mem_courses[code] = dict(existing)

    db = _get_db()
    if db is not None:
        try:
            db["courses"].update_one({"course_code": code}, {"$set": existing})
        except Exception as exc:
            logger.error(f"Error updating course {code}: {exc}")
            return {"error": "Failed to update course"}

    return {
        "success": True,
        "message": "Course updated successfully",
        "course": {**existing, "enrolled_count": _count_active_enrollments(code)},
    }


def archive_course(course_code, archive=True):
    new_status = "Archived" if archive else "Active"
    return update_course(course_code, status=new_status)


# ==========================================
# 3. ENROLLMENT MANAGEMENT
# ==========================================
def enroll_student(
    reg_no,
    course_code,
    semester=None,
    academic_year=None,
    enrolled_by="admin",
):
    reg = str(reg_no or "").strip()
    code = str(course_code or "").strip().upper()

    if not reg or not code:
        return {"error": "Registration number and course code are required"}

    student = search_student(reg)
    if not student:
        return {"error": f"Student '{reg}' not found"}

    course = get_course(code)
    if not course:
        return {"error": f"Course '{code}' not found"}

    if course.get("status") == "Archived":
        return {"error": f"Cannot enroll in archived course '{code}'"}

    sem = str(semester or course.get("semester") or "1").strip()
    year = str(academic_year or course.get("academic_year") or "2025-2026").strip()

    enrollment_obj = Enrollment(
        reg_no=reg,
        course_code=code,
        semester=sem,
        academic_year=year,
        status="Enrolled",
        enrolled_by=enrolled_by,
    )
    eid = enrollment_obj.enrollment_id

    # Duplicate check
    db = _get_db()
    if db is not None:
        existing = db["enrollments"].find_one({"enrollment_id": eid})
    else:
        existing = _mem_enrollments.get(eid)

    if existing and existing.get("status") == "Enrolled":
        return {"error": f"Student {reg} is already enrolled in {code} for Sem {sem} ({year})"}

    # Capacity check
    active_count = _count_active_enrollments(code)
    if active_count >= int(course.get("capacity", 60)):
        return {"error": f"Course {code} has reached its maximum capacity ({course['capacity']})"}

    doc = enrollment_obj.to_dict()
    _mem_enrollments[eid] = doc

    if db is not None:
        try:
            db["enrollments"].update_one(
                {"enrollment_id": eid},
                {"$set": doc},
                upsert=True,
            )
        except Exception as exc:
            logger.error(f"Error saving enrollment {eid}: {exc}")
            return {"error": "Failed to enroll student"}

    return {
        "success": True,
        "message": f"Enrolled {student['name']} ({reg}) in {code}",
        "enrollment": {
            **doc,
            "student_name": student.get("name", ""),
            "course_name": course.get("course_name", ""),
            "branch": course.get("branch", ""),
            "credits": course.get("credits", 3),
        },
    }


def is_student_enrolled(reg_no, course_code):
    reg = str(reg_no or "").strip()
    code = str(course_code or "").strip().upper()
    db = _get_db()
    if db is not None:
        try:
            doc = db["enrollments"].find_one(
                {"reg_no": reg, "course_code": code, "status": "Enrolled"}
            )
            if doc:
                return True
        except Exception:
            pass
    return any(
        e.get("reg_no") == reg
        and e.get("course_code") == code
        and e.get("status") == "Enrolled"
        for e in _mem_enrollments.values()
    )


def list_enrollments(user=None, reg_no=None, course_code=None, semester=None):
    db = _get_db()
    raw = []
    if db is not None:
        try:
            for doc in db["enrollments"].find():
                e = Enrollment.from_dict(doc)
                if e:
                    raw.append(e.to_dict())
        except Exception:
            raw = [Enrollment.from_dict(d).to_dict() for d in _mem_enrollments.values()]
    else:
        raw = [Enrollment.from_dict(d).to_dict() for d in _mem_enrollments.values()]

    results = []
    for e in raw:
        if e.get("status") != "Enrolled":
            continue
        if reg_no and e.get("reg_no") != str(reg_no).strip():
            continue
        if course_code and e.get("course_code") != str(course_code).strip().upper():
            continue
        if semester and semester != "All" and str(e.get("semester")) != str(semester).strip():
            continue

        course = get_course(e["course_code"]) or {}
        student = search_student(e["reg_no"]) or {}

        if user:
            role = user.get("role")
            if role == "Student" and e.get("reg_no") != user.get("linked_reg_no"):
                continue
            if role == "Faculty" and not can_manage_course(user, course):
                continue

        results.append({
            **e,
            "student_name": student.get("name", e["reg_no"]),
            "course_name": course.get("course_name", e["course_code"]),
            "branch": course.get("branch", student.get("branch", "")),
            "credits": course.get("credits", 3),
        })

    return results


def unenroll_student(enrollment_id):
    eid = str(enrollment_id or "").strip()
    if not eid:
        return {"error": "enrollment_id is required"}

    db = _get_db()
    found = False
    if eid in _mem_enrollments:
        del _mem_enrollments[eid]
        found = True

    if db is not None:
        try:
            res = db["enrollments"].delete_one({"enrollment_id": eid})
            if res.deleted_count > 0:
                found = True
        except Exception as exc:
            logger.error(f"Error deleting enrollment {eid}: {exc}")

    if not found:
        return {"error": "Enrollment record not found"}
    return {"success": True, "message": "Enrollment removed successfully"}


# ==========================================
# 4. ATTENDANCE MANAGEMENT & FORMULA
# ==========================================
def compute_attendance_metrics(records, late_weight=None):
    """
    Calculate attendance percentage from actual attendance records:
      Formula:
        Effective Sessions = Present + Absent + Late  (Excused sessions are excluded from penalty)
        Weighted Attended  = Present + (Late * late_weight)
        Attendance %       = (Weighted Attended / Effective Sessions) * 100
    """
    if late_weight is None:
        late_weight = get_grading_scale().late_attendance_weight

    present = 0
    absent = 0
    late = 0
    excused = 0

    for r in records:
        st = r.get("status")
        if st == "Present":
            present += 1
        elif st == "Absent":
            absent += 1
        elif st == "Late":
            late += 1
        elif st == "Excused":
            excused += 1

    total_sessions = present + absent + late + excused
    effective_sessions = present + absent + late
    weighted_attended = present + (late * float(late_weight))

    if effective_sessions > 0:
        pct = round((weighted_attended / effective_sessions) * 100.0, 2)
    elif excused > 0:
        pct = 100.0
    else:
        pct = 0.0

    return {
        "total_sessions": total_sessions,
        "effective_sessions": effective_sessions,
        "present": present,
        "absent": absent,
        "late": late,
        "excused": excused,
        "attendance_percentage": pct,
    }


def _sync_student_overall_attendance(reg_no):
    """Synchronize the student's aggregate attendance percentage back to their Student profile."""
    records = list_attendance(reg_no=reg_no)
    if not records:
        return
    metrics = compute_attendance_metrics(records)
    student = search_student(reg_no)
    if student:
        update_student(
            reg_no,
            student["name"],
            student["age"],
            student["branch"],
            attendance_pct=metrics["attendance_percentage"],
        )


def record_attendance(
    reg_no,
    course_code,
    date,
    status="Present",
    session="Lecture",
    remarks="",
    recorded_by="faculty",
    allow_update=False,
):
    reg = str(reg_no or "").strip()
    code = str(course_code or "").strip().upper()
    dt = str(date or "").strip()
    sess = str(session or "Lecture").strip()

    if not reg or not code or not dt:
        return {"error": "reg_no, course_code, and date are required"}

    if not DATE_REGEX.match(dt):
        return {"error": "Date must be in YYYY-MM-DD format"}

    if status not in AttendanceRecord.VALID_STATUSES:
        return {
            "error": f"Status must be one of: {', '.join(sorted(AttendanceRecord.VALID_STATUSES))}"
        }

    if sess not in AttendanceRecord.VALID_SESSIONS:
        return {
            "error": f"Session must be one of: {', '.join(sorted(AttendanceRecord.VALID_SESSIONS))}"
        }

    student = search_student(reg)
    if not student:
        return {"error": f"Student '{reg}' not found"}

    course = get_course(code)
    if not course:
        return {"error": f"Course '{code}' not found"}

    if not is_student_enrolled(reg, code):
        return {
            "error": f"Student '{reg}' is not enrolled in course '{code}'"
        }

    rec_obj = AttendanceRecord(
        reg_no=reg,
        course_code=code,
        date=dt,
        status=status,
        session=sess,
        remarks=remarks,
        recorded_by=recorded_by,
    )
    rid = rec_obj.record_id

    db = _get_db()
    if db is not None:
        existing = db["attendance"].find_one({"record_id": rid})
    else:
        existing = _mem_attendance.get(rid)

    if existing and not allow_update:
        return {
            "error": f"Attendance already recorded for student {reg} in {code} on {dt} ({sess})"
        }

    doc = rec_obj.to_dict()
    if existing:
        doc["created_at"] = existing.get("created_at", doc["created_at"])

    _mem_attendance[rid] = doc

    if db is not None:
        try:
            db["attendance"].update_one(
                {"record_id": rid},
                {"$set": doc},
                upsert=True,
            )
        except Exception as exc:
            logger.error(f"Error saving attendance {rid}: {exc}")
            return {"error": "Failed to save attendance record"}

    _sync_student_overall_attendance(reg)

    return {
        "success": True,
        "message": "Attendance updated successfully"
        if existing
        else "Attendance recorded successfully",
        "attendance": {
            **doc,
            "student_name": student.get("name", ""),
            "course_name": course.get("course_name", ""),
        },
    }


def list_attendance(user=None, reg_no=None, course_code=None, date=None):
    db = _get_db()
    raw = []
    if db is not None:
        try:
            for doc in db["attendance"].find():
                a = AttendanceRecord.from_dict(doc)
                if a:
                    raw.append(a.to_dict())
        except Exception:
            raw = [
                AttendanceRecord.from_dict(d).to_dict()
                for d in _mem_attendance.values()
            ]
    else:
        raw = [
            AttendanceRecord.from_dict(d).to_dict()
            for d in _mem_attendance.values()
        ]

    results = []
    for a in raw:
        if reg_no and a.get("reg_no") != str(reg_no).strip():
            continue
        if course_code and a.get("course_code") != str(course_code).strip().upper():
            continue
        if date and a.get("date") != str(date).strip():
            continue

        course = get_course(a["course_code"]) or {}
        student = search_student(a["reg_no"]) or {}

        if user:
            role = user.get("role")
            if role == "Student" and a.get("reg_no") != user.get("linked_reg_no"):
                continue
            if role == "Faculty" and not can_manage_course(user, course):
                continue

        results.append({
            **a,
            "student_name": student.get("name", a["reg_no"]),
            "course_name": course.get("course_name", a["course_code"]),
            "branch": course.get("branch", student.get("branch", "")),
        })

    results.sort(key=lambda x: (x.get("date", ""), x.get("reg_no", "")), reverse=True)
    return results


def get_attendance_report(user=None, course_code=None, reg_no=None):
    """Generate course-wise and student-wise attendance summaries from actual attendance records."""
    records = list_attendance(user=user, reg_no=reg_no, course_code=course_code)
    scale = get_grading_scale()
    threshold = scale.min_attendance_threshold

    by_course = {}
    by_student = {}

    for r in records:
        cc = r["course_code"]
        by_course.setdefault(cc, []).append(r)

        rn = r["reg_no"]
        by_student.setdefault(rn, []).append(r)

    course_summaries = []
    for cc, recs in sorted(by_course.items()):
        course = get_course(cc) or {}
        metrics = compute_attendance_metrics(recs, scale.late_attendance_weight)
        course_summaries.append({
            "course_code": cc,
            "course_name": course.get("course_name", cc),
            "branch": course.get("branch", ""),
            **metrics,
        })

    student_summaries = []
    for rn, recs in sorted(by_student.items()):
        student = search_student(rn) or {}
        metrics = compute_attendance_metrics(recs, scale.late_attendance_weight)
        student_summaries.append({
            "reg_no": rn,
            "student_name": student.get("name", rn),
            "branch": student.get("branch", ""),
            **metrics,
            "below_threshold": metrics["attendance_percentage"] < threshold,
        })

    return {
        "formula": "Attendance % = ((Present + 0.5 * Late) / (Present + Absent + Late)) * 100 (Excused excluded)",
        "min_attendance_threshold": threshold,
        "course_summaries": course_summaries,
        "student_summaries": student_summaries,
    }


# ==========================================
# 5. GRADES & GPA / CGPA MANAGEMENT
# ==========================================
def record_grade(
    reg_no,
    course_code,
    assessment_type="Overall",
    marks_obtained=0.0,
    max_marks=100.0,
    semester=None,
    academic_year=None,
    recorded_by="faculty",
    allow_update=False,
):
    reg = str(reg_no or "").strip()
    code = str(course_code or "").strip().upper()
    assess = str(assessment_type or "Overall").strip()

    if not reg or not code:
        return {"error": "reg_no and course_code are required"}

    if assess not in GradeRecord.VALID_ASSESSMENTS:
        return {
            "error": f"assessment_type must be one of: {', '.join(sorted(GradeRecord.VALID_ASSESSMENTS))}"
        }

    try:
        marks_val = float(marks_obtained)
        max_val = float(max_marks)
    except (ValueError, TypeError):
        return {"error": "marks_obtained and max_marks must be valid numbers"}

    if max_val <= 0 or max_val > 1000:
        return {"error": "max_marks must be greater than 0 and at most 1000"}

    if marks_val < 0 or marks_val > max_val:
        return {
            "error": f"marks_obtained ({marks_val}) must be between 0 and max_marks ({max_val})"
        }

    student = search_student(reg)
    if not student:
        return {"error": f"Student '{reg}' not found"}

    course = get_course(code)
    if not course:
        return {"error": f"Course '{code}' not found"}

    if not is_student_enrolled(reg, code):
        return {
            "error": f"Student '{reg}' is not enrolled in course '{code}'"
        }

    sem = str(semester or course.get("semester") or "1").strip()
    year = str(academic_year or course.get("academic_year") or "2025-2026").strip()
    credits = float(course.get("credits", 3.0))

    pct = round((marks_val / max_val) * 100.0, 2)
    scale = get_grading_scale()
    eval_res = scale.evaluate_percentage(pct)

    grade_obj = GradeRecord(
        reg_no=reg,
        course_code=code,
        assessment_type=assess,
        marks_obtained=marks_val,
        max_marks=max_val,
        credits=credits,
        percentage=pct,
        letter_grade=eval_res["letter_grade"],
        grade_points=eval_res["grade_points"],
        semester=sem,
        academic_year=year,
        recorded_by=recorded_by,
    )
    gid = grade_obj.grade_id

    db = _get_db()
    if db is not None:
        existing = db["grades"].find_one({"grade_id": gid})
    else:
        existing = _mem_grades.get(gid)

    if existing and not allow_update:
        return {
            "error": f"Grade for {assess} already recorded for student {reg} in {code}"
        }

    doc = grade_obj.to_dict()
    if existing:
        doc["created_at"] = existing.get("created_at", doc["created_at"])

    _mem_grades[gid] = doc

    if db is not None:
        try:
            db["grades"].update_one(
                {"grade_id": gid},
                {"$set": doc},
                upsert=True,
            )
        except Exception as exc:
            logger.error(f"Error saving grade {gid}: {exc}")
            return {"error": "Failed to save grade record"}

    # Recompute and sync student's credit-weighted CGPA
    gpa_summary = calculate_student_gpa(reg)
    if gpa_summary.get("cgpa") is not None:
        update_student(
            reg,
            student["name"],
            student["age"],
            student["branch"],
            gpa=gpa_summary["cgpa"],
        )

    return {
        "success": True,
        "message": "Grade updated successfully"
        if existing
        else "Grade recorded successfully",
        "grade": {
            **doc,
            "student_name": student.get("name", ""),
            "course_name": course.get("course_name", ""),
        },
        "updated_cgpa": gpa_summary.get("cgpa"),
    }


def list_grades(user=None, reg_no=None, course_code=None, semester=None):
    db = _get_db()
    raw = []
    if db is not None:
        try:
            for doc in db["grades"].find():
                g = GradeRecord.from_dict(doc)
                if g:
                    raw.append(g.to_dict())
        except Exception:
            raw = [GradeRecord.from_dict(d).to_dict() for d in _mem_grades.values()]
    else:
        raw = [GradeRecord.from_dict(d).to_dict() for d in _mem_grades.values()]

    scale = get_grading_scale()
    results = []
    for g in raw:
        if reg_no and g.get("reg_no") != str(reg_no).strip():
            continue
        if course_code and g.get("course_code") != str(course_code).strip().upper():
            continue
        if semester and semester != "All" and str(g.get("semester")) != str(semester).strip():
            continue

        course = get_course(g["course_code"]) or {}
        student = search_student(g["reg_no"]) or {}

        if user:
            role = user.get("role")
            if role == "Student" and g.get("reg_no") != user.get("linked_reg_no"):
                continue
            if role == "Faculty" and not can_manage_course(user, course):
                continue

        # Re-evaluate against active grading scale dynamically
        eval_res = scale.evaluate_percentage(g.get("percentage", 0.0))

        results.append({
            **g,
            "letter_grade": eval_res["letter_grade"],
            "grade_points": eval_res["grade_points"],
            "student_name": student.get("name", g["reg_no"]),
            "course_name": course.get("course_name", g["course_code"]),
            "branch": course.get("branch", student.get("branch", "")),
        })

    return results


def calculate_student_gpa(reg_no, semester=None):
    """
    Compute credit-weighted SGPA / CGPA from actual grade records using the active GradingScale:
      1. Aggregate marks_obtained and max_marks per (course_code, semester, academic_year).
      2. Compute course percentage = (sum(marks_obtained) / sum(max_marks)) * 100.
      3. Map course percentage to course_grade_points via active GradingScale.
      4. GPA / CGPA = sum(course_credits * course_grade_points) / sum(course_credits).
    """
    reg = str(reg_no or "").strip()
    grades = list_grades(reg_no=reg, semester=semester)
    scale = get_grading_scale()

    course_buckets = {}
    for g in grades:
        key = (g["course_code"], g.get("semester", "1"), g.get("academic_year", "2025-2026"))
        bucket = course_buckets.setdefault(
            key,
            {
                "course_code": g["course_code"],
                "course_name": g.get("course_name", g["course_code"]),
                "semester": g.get("semester", "1"),
                "academic_year": g.get("academic_year", "2025-2026"),
                "credits": float(g.get("credits", 3.0)),
                "marks_obtained": 0.0,
                "max_marks": 0.0,
            },
        )
        bucket["marks_obtained"] += float(g.get("marks_obtained", 0.0))
        bucket["max_marks"] += float(g.get("max_marks", 0.0))

    course_results = []
    total_weighted_points = 0.0
    total_credits = 0.0
    by_semester = {}

    for bucket in course_buckets.values():
        if bucket["max_marks"] <= 0:
            continue
        pct = round((bucket["marks_obtained"] / bucket["max_marks"]) * 100.0, 2)
        eval_res = scale.evaluate_percentage(pct)
        gp = float(eval_res["grade_points"])
        cred = float(bucket["credits"])

        total_weighted_points += cred * gp
        total_credits += cred

        sem_key = str(bucket["semester"])
        sem_entry = by_semester.setdefault(
            sem_key, {"weighted": 0.0, "credits": 0.0}
        )
        sem_entry["weighted"] += cred * gp
        sem_entry["credits"] += cred

        course_results.append({
            **bucket,
            "percentage": pct,
            "letter_grade": eval_res["letter_grade"],
            "grade_points": gp,
        })

    cgpa = (
        round(total_weighted_points / total_credits, 2)
        if total_credits > 0
        else None
    )

    semester_gpas = {
        f"Semester {sem}": round(vals["weighted"] / vals["credits"], 2)
        for sem, vals in sorted(by_semester.items())
        if vals["credits"] > 0
    }

    return {
        "reg_no": reg,
        "scale_name": scale.scale_name,
        "max_grade_points": scale.max_grade_points,
        "formula": "CGPA = sum(Course Credits * Grade Points) / sum(Course Credits)",
        "cgpa": cgpa,
        "total_credits": total_credits,
        "semester_gpas": semester_gpas,
        "courses": course_results,
    }


def get_academic_performance_report(user=None, course_code=None, reg_no=None):
    """Generate course-wise and student-wise academic performance summaries."""
    grades = list_grades(user=user, reg_no=reg_no, course_code=course_code)
    scale = get_grading_scale()

    by_course = {}
    student_regs = set()
    for g in grades:
        by_course.setdefault(g["course_code"], []).append(g)
        student_regs.add(g["reg_no"])

    course_reports = []
    for cc, recs in sorted(by_course.items()):
        course = get_course(cc) or {}
        pcts = [float(r.get("percentage", 0.0)) for r in recs]
        avg_pct = round(sum(pcts) / len(pcts), 2) if pcts else 0.0
        pass_count = sum(1 for r in recs if r.get("letter_grade") != "F")
        course_reports.append({
            "course_code": cc,
            "course_name": course.get("course_name", cc),
            "branch": course.get("branch", ""),
            "credits": course.get("credits", 3.0),
            "assessments_recorded": len(recs),
            "average_percentage": avg_pct,
            "pass_rate": round((pass_count / len(recs)) * 100.0, 1) if recs else 0.0,
        })

    student_reports = []
    for rn in sorted(student_regs):
        student = search_student(rn) or {}
        gpa_info = calculate_student_gpa(rn)
        student_reports.append({
            "reg_no": rn,
            "student_name": student.get("name", rn),
            "branch": student.get("branch", ""),
            "cgpa": gpa_info["cgpa"],
            "total_credits": gpa_info["total_credits"],
            "semester_gpas": gpa_info["semester_gpas"],
            "courses_graded": len(gpa_info["courses"]),
        })

    return {
        "scale_name": scale.scale_name,
        "formula": "CGPA = sum(Course Credits * Grade Points) / sum(Course Credits)",
        "course_reports": course_reports,
        "student_reports": student_reports,
    }

