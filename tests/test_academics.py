import os
import sys

os.environ["STUDENTDB_TEST_MODE"] = "1"
os.environ["SECRET_KEY"] = "test-secret-key-for-unit-and-integration-suite-2026"

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from backend.api.app import app, clear_rate_limits
from services.student_service import reset_test_students, add_student, search_student
from services.auth_service import reset_test_auth
from services.academic_service import reset_test_academics


@pytest.fixture(autouse=True)
def isolated_academic_env():
    reset_test_students()
    reset_test_auth()
    reset_test_academics()
    clear_rate_limits()

    # Seed students
    add_student("REG2026001", "101", "Aarav Sharma", 20, "CSE", semester="3")
    add_student("REG2026002", "102", "Meera Nair", 20, "CSE", semester="3")
    add_student("REG2026003", "201", "Vikram Rao", 21, "ECE", semester="3")
    yield


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def _login(client, username, password):
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    data = resp.get_json()
    return resp, data["csrf_token"]


# ==========================================
# 1. COURSE CRUD, ARCHIVING & RBAC PERMISSIONS
# ==========================================
def test_course_crud_validation_archiving_and_permissions(client):
    _, admin_csrf = _login(client, "admin", "Admin@123")

    # Invalid course creation (negative credits)
    bad_resp = client.post(
        "/api/v1/courses",
        headers={"X-CSRF-Token": admin_csrf},
        json={
            "course_code": "CS301",
            "course_name": "Database Systems",
            "branch": "CSE",
            "credits": -4,
        },
    )
    assert bad_resp.status_code == 400

    # Valid CSE course creation
    c1_resp = client.post(
        "/api/v1/courses",
        headers={"X-CSRF-Token": admin_csrf},
        json={
            "course_code": "CS301",
            "course_name": "Database Management Systems",
            "branch": "CSE",
            "credits": 4,
            "semester": "3",
            "faculty_username": "faculty_cse",
            "capacity": 2,
        },
    )
    assert c1_resp.status_code == 201

    # Duplicate course_code rejected
    dup_resp = client.post(
        "/api/v1/courses",
        headers={"X-CSRF-Token": admin_csrf},
        json={
            "course_code": "CS301",
            "course_name": "Duplicate DBMS",
            "branch": "CSE",
            "credits": 4,
        },
    )
    assert dup_resp.status_code == 400
    assert "already exists" in dup_resp.get_json()["message"]

    # Create an ECE course
    c2_resp = client.post(
        "/api/v1/courses",
        headers={"X-CSRF-Token": admin_csrf},
        json={
            "course_code": "EC301",
            "course_name": "Digital Signal Processing",
            "branch": "ECE",
            "credits": 3,
            "semester": "3",
            "capacity": 30,
        },
    )
    assert c2_resp.status_code == 201

    # Archive EC301 and verify it is hidden from default active course listing
    arch_resp = client.patch(
        "/api/v1/courses/EC301/archive",
        headers={"X-CSRF-Token": admin_csrf},
        json={"archive": True},
    )
    assert arch_resp.status_code == 200
    assert arch_resp.get_json()["course"]["status"] == "Archived"

    active_list = client.get("/api/v1/courses").get_json()["courses"]
    assert len(active_list) == 1
    assert active_list[0]["course_code"] == "CS301"

    # Unarchive EC301
    client.patch(
        "/api/v1/courses/EC301/archive",
        headers={"X-CSRF-Token": admin_csrf},
        json={"archive": False},
    )

    # Faculty (assigned to CSE) sees only CS301 and cannot create/archive courses or view EC301
    _, fac_csrf = _login(client, "faculty_cse", "Faculty@123")
    fac_courses = client.get("/api/v1/courses").get_json()["courses"]
    assert len(fac_courses) == 1
    assert fac_courses[0]["course_code"] == "CS301"

    assert client.get("/api/v1/courses/EC301").status_code == 403
    assert (
        client.post(
            "/api/v1/courses",
            headers={"X-CSRF-Token": fac_csrf},
            json={
                "course_code": "CS399",
                "course_name": "Unauthorized Course",
                "branch": "CSE",
            },
        ).status_code
        == 403
    )


# ==========================================
# 2. ENROLLMENT VALIDATION, DUPLICATES & CAPACITY
# ==========================================
def test_enrollment_referential_checks_duplicates_and_capacity(client):
    _, admin_csrf = _login(client, "admin", "Admin@123")

    # Create course with capacity = 1
    client.post(
        "/api/v1/courses",
        headers={"X-CSRF-Token": admin_csrf},
        json={
            "course_code": "CS301",
            "course_name": "Algorithms",
            "branch": "CSE",
            "credits": 4,
            "semester": "3",
            "capacity": 1,
        },
    )

    # Non-existent student -> 404
    missing_stu = client.post(
        "/api/v1/enrollments",
        headers={"X-CSRF-Token": admin_csrf},
        json={"reg_no": "REG999999", "course_code": "CS301"},
    )
    assert missing_stu.status_code == 404

    # Non-existent course -> 404
    missing_crs = client.post(
        "/api/v1/enrollments",
        headers={"X-CSRF-Token": admin_csrf},
        json={"reg_no": "REG2026001", "course_code": "CS999"},
    )
    assert missing_crs.status_code == 404

    # Valid enrollment #1 -> 201
    enr1 = client.post(
        "/api/v1/enrollments",
        headers={"X-CSRF-Token": admin_csrf},
        json={"reg_no": "REG2026001", "course_code": "CS301"},
    )
    assert enr1.status_code == 201

    # Duplicate enrollment for same student & course -> 400
    dup_enr = client.post(
        "/api/v1/enrollments",
        headers={"X-CSRF-Token": admin_csrf},
        json={"reg_no": "REG2026001", "course_code": "CS301"},
    )
    assert dup_enr.status_code == 400
    assert "already enrolled" in dup_enr.get_json()["message"]

    # Enrolling 2nd student when capacity=1 -> 400
    cap_enr = client.post(
        "/api/v1/enrollments",
        headers={"X-CSRF-Token": admin_csrf},
        json={"reg_no": "REG2026002", "course_code": "CS301"},
    )
    assert cap_enr.status_code == 400
    assert "capacity" in cap_enr.get_json()["message"].lower()


# ==========================================
# 3. ATTENDANCE TRACKING, DUPLICATE PREVENTION & FORMULA
# ==========================================
def test_attendance_lifecycle_duplicate_prevention_and_percentage_formula(client):
    _, admin_csrf = _login(client, "admin", "Admin@123")
    client.post(
        "/api/v1/courses",
        headers={"X-CSRF-Token": admin_csrf},
        json={
            "course_code": "CS301",
            "course_name": "Operating Systems",
            "branch": "CSE",
            "credits": 4,
            "faculty_username": "faculty_cse",
        },
    )
    client.post(
        "/api/v1/enrollments",
        headers={"X-CSRF-Token": admin_csrf},
        json={"reg_no": "REG2026001", "course_code": "CS301"},
    )

    # Switch to Faculty account to record classroom attendance
    _, fac_csrf = _login(client, "faculty_cse", "Faculty@123")

    # Recording attendance for unenrolled student REG2026002 -> 400
    unenrolled_resp = client.post(
        "/api/v1/attendance",
        headers={"X-CSRF-Token": fac_csrf},
        json={
            "reg_no": "REG2026002",
            "course_code": "CS301",
            "date": "2026-10-01",
            "status": "Present",
        },
    )
    assert unenrolled_resp.status_code == 400
    assert "not enrolled" in unenrolled_resp.get_json()["message"]

    # Record 4 sessions for REG2026001: Present, Late, Absent, Excused
    sessions = [
        ("2026-10-01", "Present"),
        ("2026-10-02", "Late"),
        ("2026-10-03", "Absent"),
        ("2026-10-04", "Excused"),
    ]
    for dt, st in sessions:
        r = client.post(
            "/api/v1/attendance",
            headers={"X-CSRF-Token": fac_csrf},
            json={
                "reg_no": "REG2026001",
                "course_code": "CS301",
                "date": dt,
                "status": st,
                "session": "Lecture",
            },
        )
        assert r.status_code == 201

    # Duplicate POST for same student, course, date, and session -> 400
    dup_att = client.post(
        "/api/v1/attendance",
        headers={"X-CSRF-Token": fac_csrf},
        json={
            "reg_no": "REG2026001",
            "course_code": "CS301",
            "date": "2026-10-03",
            "status": "Present",
            "session": "Lecture",
        },
    )
    assert dup_att.status_code == 400
    assert "already recorded" in dup_att.get_json()["message"]

    # Verify attendance report formula:
    # Effective sessions = 3 (1 Present + 1 Late + 1 Absent; Excused excluded)
    # Weighted attended = 1 + (1 * 0.5) = 1.5 -> (1.5 / 3) * 100 = 50.0%
    rep_resp = client.get("/api/v1/attendance/report?course_code=CS301")
    assert rep_resp.status_code == 200
    rep = rep_resp.get_json()
    stu_summary = rep["student_summaries"][0]
    assert stu_summary["reg_no"] == "REG2026001"
    assert stu_summary["total_sessions"] == 4
    assert stu_summary["effective_sessions"] == 3
    assert stu_summary["attendance_percentage"] == 50.0
    assert stu_summary["below_threshold"] is True

    # Verify student profile attendance_pct was automatically synchronized
    assert search_student("REG2026001")["attendance_pct"] == 50.0

    # Update the 2026-10-03 Absent record to Present via PUT -> 200
    # Now: 2 Present + 1 Late (0.5) = 2.5 / 3 = 83.33%
    upd_att = client.put(
        "/api/v1/attendance",
        headers={"X-CSRF-Token": fac_csrf},
        json={
            "reg_no": "REG2026001",
            "course_code": "CS301",
            "date": "2026-10-03",
            "status": "Present",
            "session": "Lecture",
        },
    )
    assert upd_att.status_code == 200
    assert search_student("REG2026001")["attendance_pct"] == 83.33

    # Student role isolation: student_demo (REG2026001) can view own attendance, 403 on REG2026002
    _login(client, "student_demo", "Student@123")
    assert client.get("/api/v1/attendance").status_code == 200
    assert client.get("/api/v1/attendance?reg_no=REG2026002").status_code == 403
    assert client.get("/api/v1/attendance/report?reg_no=REG2026002").status_code == 403


# ==========================================
# 4. GRADES, CONFIGURABLE GRADING SCALE & GPA/CGPA
# ==========================================
def test_grades_validation_credit_weighted_cgpa_and_configurable_scale(client):
    _, admin_csrf = _login(client, "admin", "Admin@123")

    # Create two CSE courses: CS301 (4 credits) and CS302 (2 credits), plus EC301 (3 credits)
    client.post(
        "/api/v1/courses",
        headers={"X-CSRF-Token": admin_csrf},
        json={
            "course_code": "CS301",
            "course_name": "Computer Networks",
            "branch": "CSE",
            "credits": 4,
            "semester": "3",
        },
    )
    client.post(
        "/api/v1/courses",
        headers={"X-CSRF-Token": admin_csrf},
        json={
            "course_code": "CS302",
            "course_name": "Software Engineering",
            "branch": "CSE",
            "credits": 2,
            "semester": "3",
        },
    )
    client.post(
        "/api/v1/courses",
        headers={"X-CSRF-Token": admin_csrf},
        json={
            "course_code": "EC301",
            "course_name": "Analog Circuits",
            "branch": "ECE",
            "credits": 3,
            "semester": "3",
        },
    )

    # Enroll REG2026001 in CS301 and CS302
    client.post(
        "/api/v1/enrollments",
        headers={"X-CSRF-Token": admin_csrf},
        json={"reg_no": "REG2026001", "course_code": "CS301"},
    )
    client.post(
        "/api/v1/enrollments",
        headers={"X-CSRF-Token": admin_csrf},
        json={"reg_no": "REG2026001", "course_code": "CS302"},
    )

    # Switch to Faculty (assigned to CSE)
    _, fac_csrf = _login(client, "faculty_cse", "Faculty@123")

    # Faculty cannot record grades for unassigned EC301 -> 403
    assert (
        client.post(
            "/api/v1/grades",
            headers={"X-CSRF-Token": fac_csrf},
            json={
                "reg_no": "REG2026003",
                "course_code": "EC301",
                "marks_obtained": 80,
                "max_marks": 100,
            },
        ).status_code
        == 403
    )

    # Invalid marks (> max_marks) -> 400
    assert (
        client.post(
            "/api/v1/grades",
            headers={"X-CSRF-Token": fac_csrf},
            json={
                "reg_no": "REG2026001",
                "course_code": "CS301",
                "marks_obtained": 120,
                "max_marks": 100,
            },
        ).status_code
        == 400
    )

    # Record CS301 (4 credits): 85/100 (85% -> A+ -> 9.0 GP on 10-point scale)
    g1 = client.post(
        "/api/v1/grades",
        headers={"X-CSRF-Token": fac_csrf},
        json={
            "reg_no": "REG2026001",
            "course_code": "CS301",
            "assessment_type": "Overall",
            "marks_obtained": 85,
            "max_marks": 100,
        },
    )
    assert g1.status_code == 201
    assert g1.get_json()["grade"]["letter_grade"] == "A+"
    assert g1.get_json()["grade"]["grade_points"] == 9.0

    # Record CS302 (2 credits): 72/100 (72% -> A -> 8.0 GP on 10-point scale)
    g2 = client.post(
        "/api/v1/grades",
        headers={"X-CSRF-Token": fac_csrf},
        json={
            "reg_no": "REG2026001",
            "course_code": "CS302",
            "assessment_type": "Overall",
            "marks_obtained": 72,
            "max_marks": 100,
        },
    )
    assert g2.status_code == 201
    assert g2.get_json()["grade"]["letter_grade"] == "A"
    assert g2.get_json()["grade"]["grade_points"] == 8.0

    # Verify credit-weighted CGPA: ((4 * 9.0) + (2 * 8.0)) / (4 + 2) = 52 / 6 = 8.67
    gpa_resp = client.get("/api/v1/grades/gpa/REG2026001")
    assert gpa_resp.status_code == 200
    gpa_data = gpa_resp.get_json()
    assert gpa_data["cgpa"] == 8.67
    assert gpa_data["total_credits"] == 6.0
    assert search_student("REG2026001")["gpa"] == 8.67

    # Admin updates grading scale to a 4.0 US GPA Scale at runtime
    _, admin_csrf = _login(client, "admin", "Admin@123")
    scale_upd = client.put(
        "/api/v1/academics/grading-scale",
        headers={"X-CSRF-Token": admin_csrf},
        json={
            "scale_name": "Standard 4.0 GPA Scale",
            "max_grade_points": 4.0,
            "late_attendance_weight": 0.5,
            "min_attendance_threshold": 75.0,
            "bands": [
                {"min_percentage": 80.0, "letter_grade": "A", "grade_points": 4.0},
                {"min_percentage": 70.0, "letter_grade": "B", "grade_points": 3.0},
                {"min_percentage": 60.0, "letter_grade": "C", "grade_points": 2.0},
                {"min_percentage": 50.0, "letter_grade": "D", "grade_points": 1.0},
                {"min_percentage": 0.0, "letter_grade": "F", "grade_points": 0.0},
            ],
        },
    )
    assert scale_upd.status_code == 200

    # Re-querying GPA dynamically applies the 4.0 scale: ((4 * 4.0) + (2 * 3.0)) / 6 = 22 / 6 = 3.67
    gpa_4scale = client.get("/api/v1/grades/gpa/REG2026001").get_json()
    assert gpa_4scale["scale_name"] == "Standard 4.0 GPA Scale"
    assert gpa_4scale["cgpa"] == 3.67

    # Student role isolation on grades and GPA
    _login(client, "student_demo", "Student@123")
    assert client.get("/api/v1/grades/gpa/REG2026001").status_code == 200
    assert client.get("/api/v1/grades/gpa/REG2026002").status_code == 403
    assert client.get("/api/v1/grades?reg_no=REG2026002").status_code == 403

