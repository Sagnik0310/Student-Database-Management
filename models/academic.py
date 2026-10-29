from datetime import datetime, timezone


# ==========================================
# CONFIGURABLE GRADING SCALE ENGINE
# ==========================================
DEFAULT_GRADING_SCALE = {
    "scale_name": "Standard 10-Point CBCS Scale",
    "max_grade_points": 10.0,
    "late_attendance_weight": 0.5,
    "min_attendance_threshold": 75.0,
    "bands": [
        {"min_percentage": 90.0, "letter_grade": "O", "grade_points": 10.0},
        {"min_percentage": 80.0, "letter_grade": "A+", "grade_points": 9.0},
        {"min_percentage": 70.0, "letter_grade": "A", "grade_points": 8.0},
        {"min_percentage": 60.0, "letter_grade": "B+", "grade_points": 7.0},
        {"min_percentage": 50.0, "letter_grade": "B", "grade_points": 6.0},
        {"min_percentage": 40.0, "letter_grade": "C", "grade_points": 5.0},
        {"min_percentage": 0.0, "letter_grade": "F", "grade_points": 0.0},
    ],
}


class GradingScale:
    """Encapsulates configurable grading rules separate from core application logic."""

    def __init__(self, config_dict=None):
        cfg = config_dict or DEFAULT_GRADING_SCALE
        self.scale_name = str(cfg.get("scale_name") or DEFAULT_GRADING_SCALE["scale_name"])
        self.max_grade_points = float(cfg.get("max_grade_points", 10.0))
        self.late_attendance_weight = float(cfg.get("late_attendance_weight", 0.5))
        self.min_attendance_threshold = float(cfg.get("min_attendance_threshold", 75.0))
        raw_bands = cfg.get("bands") or DEFAULT_GRADING_SCALE["bands"]
        self.bands = sorted(
            [
                {
                    "min_percentage": float(b["min_percentage"]),
                    "letter_grade": str(b["letter_grade"]).strip(),
                    "grade_points": float(b["grade_points"]),
                }
                for b in raw_bands
            ],
            key=lambda x: x["min_percentage"],
            reverse=True,
        )

    def evaluate_percentage(self, percentage):
        """Map a numeric percentage (0-100) to {letter_grade, grade_points}."""
        pct = float(percentage)
        for band in self.bands:
            if pct >= band["min_percentage"]:
                return {
                    "letter_grade": band["letter_grade"],
                    "grade_points": band["grade_points"],
                }
        return {"letter_grade": "F", "grade_points": 0.0}

    def to_dict(self):
        return {
            "scale_name": self.scale_name,
            "max_grade_points": self.max_grade_points,
            "late_attendance_weight": self.late_attendance_weight,
            "min_attendance_threshold": self.min_attendance_threshold,
            "bands": self.bands,
        }

    @staticmethod
    def validate_config(cfg):
        if not isinstance(cfg, dict):
            return "Grading configuration must be a JSON object"
        bands = cfg.get("bands")
        if not isinstance(bands, list) or len(bands) == 0:
            return "Grading scale must include a non-empty 'bands' list"
        max_gp = float(cfg.get("max_grade_points", 10.0))
        if max_gp <= 0 or max_gp > 100:
            return "max_grade_points must be between 0 and 100"

        for idx, b in enumerate(bands):
            if not isinstance(b, dict):
                return f"Band #{idx + 1} must be an object"
            if "min_percentage" not in b or "letter_grade" not in b or "grade_points" not in b:
                return f"Band #{idx + 1} requires min_percentage, letter_grade, and grade_points"
            try:
                min_p = float(b["min_percentage"])
                gp = float(b["grade_points"])
            except (ValueError, TypeError):
                return f"Band #{idx + 1} has non-numeric threshold or grade_points"
            if min_p < 0 or min_p > 100:
                return f"Band #{idx + 1} min_percentage must be between 0 and 100"
            if gp < 0 or gp > max_gp:
                return f"Band #{idx + 1} grade_points must be between 0 and {max_gp}"
            if not str(b["letter_grade"]).strip():
                return f"Band #{idx + 1} letter_grade cannot be empty"
        return None


# ==========================================
# COURSE MODEL
# ==========================================
class Course:
    VALID_STATUSES = {"Active", "Archived"}

    def __init__(
        self,
        course_code,
        course_name,
        branch,
        credits=3,
        semester="1",
        academic_year="2025-2026",
        faculty_username="",
        capacity=60,
        status="Active",
        description="",
        created_at=None,
        updated_at=None,
    ):
        self.course_code = str(course_code or "").strip().upper()
        self.course_name = str(course_name or "").strip()
        self.branch = str(branch or "").strip().upper()
        self.credits = float(credits) if credits is not None else 3.0
        self.semester = str(semester or "1").strip()
        self.academic_year = str(academic_year or "2025-2026").strip()
        self.faculty_username = str(faculty_username or "").strip()
        self.capacity = int(capacity) if capacity is not None else 60
        self.status = status if status in self.VALID_STATUSES else "Active"
        self.description = str(description or "").strip()
        now_iso = datetime.now(timezone.utc).isoformat()
        self.created_at = created_at or now_iso
        self.updated_at = updated_at or now_iso

    def to_dict(self):
        return {
            "course_code": self.course_code,
            "course_name": self.course_name,
            "branch": self.branch,
            "credits": self.credits,
            "semester": self.semester,
            "academic_year": self.academic_year,
            "faculty_username": self.faculty_username,
            "capacity": self.capacity,
            "status": self.status,
            "description": self.description,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, doc):
        if not doc:
            return None
        return cls(
            course_code=doc.get("course_code", ""),
            course_name=doc.get("course_name", ""),
            branch=doc.get("branch", ""),
            credits=doc.get("credits", 3),
            semester=doc.get("semester", "1"),
            academic_year=doc.get("academic_year", "2025-2026"),
            faculty_username=doc.get("faculty_username", ""),
            capacity=doc.get("capacity", 60),
            status=doc.get("status", "Active"),
            description=doc.get("description", ""),
            created_at=doc.get("created_at"),
            updated_at=doc.get("updated_at"),
        )


# ==========================================
# ENROLLMENT MODEL
# ==========================================
class Enrollment:
    VALID_STATUSES = {"Enrolled", "Dropped", "Completed"}

    def __init__(
        self,
        reg_no,
        course_code,
        semester="1",
        academic_year="2025-2026",
        status="Enrolled",
        enrolled_by="admin",
        enrolled_at=None,
        enrollment_id=None,
    ):
        self.reg_no = str(reg_no or "").strip()
        self.course_code = str(course_code or "").strip().upper()
        self.semester = str(semester or "1").strip()
        self.academic_year = str(academic_year or "2025-2026").strip()
        self.status = status if status in self.VALID_STATUSES else "Enrolled"
        self.enrolled_by = str(enrolled_by or "admin").strip()
        self.enrolled_at = enrolled_at or datetime.now(timezone.utc).isoformat()
        self.enrollment_id = (
            enrollment_id
            or f"{self.reg_no}:{self.course_code}:{self.semester}:{self.academic_year}"
        )

    def to_dict(self):
        return {
            "enrollment_id": self.enrollment_id,
            "reg_no": self.reg_no,
            "course_code": self.course_code,
            "semester": self.semester,
            "academic_year": self.academic_year,
            "status": self.status,
            "enrolled_by": self.enrolled_by,
            "enrolled_at": self.enrolled_at,
        }

    @classmethod
    def from_dict(cls, doc):
        if not doc:
            return None
        return cls(
            reg_no=doc.get("reg_no", ""),
            course_code=doc.get("course_code", ""),
            semester=doc.get("semester", "1"),
            academic_year=doc.get("academic_year", "2025-2026"),
            status=doc.get("status", "Enrolled"),
            enrolled_by=doc.get("enrolled_by", "admin"),
            enrolled_at=doc.get("enrolled_at"),
            enrollment_id=doc.get("enrollment_id"),
        )


# ==========================================
# ATTENDANCE RECORD MODEL
# ==========================================
class AttendanceRecord:
    VALID_STATUSES = {"Present", "Absent", "Late", "Excused"}
    VALID_SESSIONS = {"Lecture", "Lab", "Tutorial", "Morning", "Afternoon"}

    def __init__(
        self,
        reg_no,
        course_code,
        date,
        status="Present",
        session="Lecture",
        remarks="",
        recorded_by="faculty",
        created_at=None,
        updated_at=None,
        record_id=None,
    ):
        self.reg_no = str(reg_no or "").strip()
        self.course_code = str(course_code or "").strip().upper()
        self.date = str(date or "").strip()
        self.session = (
            str(session).strip()
            if str(session or "").strip() in self.VALID_SESSIONS
            else "Lecture"
        )
        self.status = status if status in self.VALID_STATUSES else "Present"
        self.remarks = str(remarks or "").strip()
        self.recorded_by = str(recorded_by or "faculty").strip()
        now_iso = datetime.now(timezone.utc).isoformat()
        self.created_at = created_at or now_iso
        self.updated_at = updated_at or now_iso
        self.record_id = (
            record_id or f"{self.reg_no}:{self.course_code}:{self.date}:{self.session}"
        )

    def to_dict(self):
        return {
            "record_id": self.record_id,
            "reg_no": self.reg_no,
            "course_code": self.course_code,
            "date": self.date,
            "session": self.session,
            "status": self.status,
            "remarks": self.remarks,
            "recorded_by": self.recorded_by,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, doc):
        if not doc:
            return None
        return cls(
            reg_no=doc.get("reg_no", ""),
            course_code=doc.get("course_code", ""),
            date=doc.get("date", ""),
            status=doc.get("status", "Present"),
            session=doc.get("session", "Lecture"),
            remarks=doc.get("remarks", ""),
            recorded_by=doc.get("recorded_by", "faculty"),
            created_at=doc.get("created_at"),
            updated_at=doc.get("updated_at"),
            record_id=doc.get("record_id"),
        )


# ==========================================
# GRADE RECORD MODEL
# ==========================================
class GradeRecord:
    VALID_ASSESSMENTS = {"Midterm", "Final", "Internal", "Assignment", "Lab", "Overall"}

    def __init__(
        self,
        reg_no,
        course_code,
        assessment_type="Overall",
        marks_obtained=0.0,
        max_marks=100.0,
        credits=3.0,
        percentage=0.0,
        letter_grade="F",
        grade_points=0.0,
        semester="1",
        academic_year="2025-2026",
        recorded_by="faculty",
        created_at=None,
        updated_at=None,
        grade_id=None,
    ):
        self.reg_no = str(reg_no or "").strip()
        self.course_code = str(course_code or "").strip().upper()
        self.assessment_type = (
            assessment_type
            if assessment_type in self.VALID_ASSESSMENTS
            else "Overall"
        )
        self.marks_obtained = float(marks_obtained)
        self.max_marks = float(max_marks)
        self.credits = float(credits)
        self.percentage = round(float(percentage), 2)
        self.letter_grade = str(letter_grade or "F").strip()
        self.grade_points = round(float(grade_points), 2)
        self.semester = str(semester or "1").strip()
        self.academic_year = str(academic_year or "2025-2026").strip()
        self.recorded_by = str(recorded_by or "faculty").strip()
        now_iso = datetime.now(timezone.utc).isoformat()
        self.created_at = created_at or now_iso
        self.updated_at = updated_at or now_iso
        self.grade_id = (
            grade_id
            or f"{self.reg_no}:{self.course_code}:{self.assessment_type}:{self.semester}:{self.academic_year}"
        )

    def to_dict(self):
        return {
            "grade_id": self.grade_id,
            "reg_no": self.reg_no,
            "course_code": self.course_code,
            "assessment_type": self.assessment_type,
            "marks_obtained": self.marks_obtained,
            "max_marks": self.max_marks,
            "credits": self.credits,
            "percentage": self.percentage,
            "letter_grade": self.letter_grade,
            "grade_points": self.grade_points,
            "semester": self.semester,
            "academic_year": self.academic_year,
            "recorded_by": self.recorded_by,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, doc):
        if not doc:
            return None
        return cls(
            reg_no=doc.get("reg_no", ""),
            course_code=doc.get("course_code", ""),
            assessment_type=doc.get("assessment_type", "Overall"),
            marks_obtained=doc.get("marks_obtained", 0.0),
            max_marks=doc.get("max_marks", 100.0),
            credits=doc.get("credits", 3.0),
            percentage=doc.get("percentage", 0.0),
            letter_grade=doc.get("letter_grade", "F"),
            grade_points=doc.get("grade_points", 0.0),
            semester=doc.get("semester", "1"),
            academic_year=doc.get("academic_year", "2025-2026"),
            recorded_by=doc.get("recorded_by", "faculty"),
            created_at=doc.get("created_at"),
            updated_at=doc.get("updated_at"),
            grade_id=doc.get("grade_id"),
        )

