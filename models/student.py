from datetime import datetime, timezone


class Student:
    """Domain model representing a student record with backward compatibility for legacy documents."""

    VALID_STATUSES = {"Active", "On Leave", "Probation", "Graduated", "Inactive"}

    def __init__(
        self,
        reg_no,
        roll_no,
        name,
        age,
        branch,
        email="",
        phone="",
        semester="",
        academic_year="",
        admission_date="",
        status="Active",
        gpa=None,
        attendance_pct=None,
        created_at=None,
        updated_at=None,
    ):
        self.reg_no = str(reg_no).strip() if reg_no is not None else ""
        self.roll_no = str(roll_no).strip() if roll_no is not None else ""
        self.name = str(name).strip() if name is not None else ""
        self.age = int(age) if age is not None and str(age).strip() != "" else 0
        self.branch = str(branch).strip() if branch is not None else ""
        self.email = str(email).strip() if email else ""
        self.phone = str(phone).strip() if phone else ""
        self.semester = str(semester).strip() if semester not in (None, "") else ""
        self.academic_year = str(academic_year).strip() if academic_year else ""
        self.admission_date = str(admission_date).strip() if admission_date else ""
        self.status = status if status in self.VALID_STATUSES else "Active"
        self.gpa = float(gpa) if gpa not in (None, "") else None
        self.attendance_pct = (
            float(attendance_pct) if attendance_pct not in (None, "") else None
        )
        now_iso = datetime.now(timezone.utc).isoformat()
        self.created_at = created_at or now_iso
        self.updated_at = updated_at or now_iso

    def to_dict(self):
        data = {
            "reg_no": self.reg_no,
            "roll_no": self.roll_no,
            "name": self.name,
            "age": self.age,
            "branch": self.branch,
            "email": self.email,
            "phone": self.phone,
            "semester": self.semester,
            "academic_year": self.academic_year,
            "admission_date": self.admission_date,
            "status": self.status,
            "gpa": self.gpa,
            "attendance_pct": self.attendance_pct,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        return data

    @classmethod
    def from_dict(cls, doc):
        if not doc:
            return None
        return cls(
            reg_no=doc.get("reg_no", ""),
            roll_no=doc.get("roll_no", ""),
            name=doc.get("name", ""),
            age=doc.get("age", 0),
            branch=doc.get("branch", ""),
            email=doc.get("email", ""),
            phone=doc.get("phone", ""),
            semester=doc.get("semester", ""),
            academic_year=doc.get("academic_year", ""),
            admission_date=doc.get("admission_date", ""),
            status=doc.get("status", "Active") or "Active",
            gpa=doc.get("gpa"),
            attendance_pct=doc.get("attendance_pct"),
            created_at=doc.get("created_at"),
            updated_at=doc.get("updated_at"),
        )

    def __str__(self):
        return (
            f"Reg: {self.reg_no} | "
            f"Roll: {self.roll_no} | "
            f"Name: {self.name} | "
            f"Age: {self.age} | "
            f"Branch: {self.branch}"
        )
