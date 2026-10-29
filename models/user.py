from datetime import datetime, timezone


class User:
    """Domain model for platform users supporting Admin, Faculty, and Student RBAC roles."""

    VALID_ROLES = {"Admin", "Faculty", "Student"}

    def __init__(
        self,
        username,
        password_hash,
        role="Student",
        full_name="",
        email="",
        assigned_branches=None,
        assigned_reg_nos=None,
        linked_reg_no="",
        is_active=True,
        tokens_valid_after=None,
        created_at=None,
        updated_at=None,
    ):
        self.username = str(username or "").strip()
        self.password_hash = str(password_hash or "")
        self.role = role if role in self.VALID_ROLES else "Student"
        self.full_name = str(full_name or self.username).strip()
        self.email = str(email or "").strip()
        self.assigned_branches = (
            [str(b).strip() for b in assigned_branches if str(b).strip()]
            if isinstance(assigned_branches, list)
            else []
        )
        self.assigned_reg_nos = (
            [str(r).strip() for r in assigned_reg_nos if str(r).strip()]
            if isinstance(assigned_reg_nos, list)
            else []
        )
        self.linked_reg_no = str(linked_reg_no or "").strip()
        self.is_active = bool(is_active)
        self.tokens_valid_after = (
            int(tokens_valid_after) if tokens_valid_after is not None else None
        )
        now_iso = datetime.now(timezone.utc).isoformat()
        self.created_at = created_at or now_iso
        self.updated_at = updated_at or now_iso

    def to_dict(self):
        """Full representation for database storage (includes password_hash and tokens_valid_after)."""
        data = {
            "username": self.username,
            "password_hash": self.password_hash,
            "role": self.role,
            "full_name": self.full_name,
            "email": self.email,
            "assigned_branches": self.assigned_branches,
            "assigned_reg_nos": self.assigned_reg_nos,
            "linked_reg_no": self.linked_reg_no,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        if self.tokens_valid_after is not None:
            data["tokens_valid_after"] = self.tokens_valid_after
        return data

    def to_public_dict(self):
        """Safe representation for API responses (never includes password_hash)."""
        return {
            "username": self.username,
            "role": self.role,
            "full_name": self.full_name,
            "email": self.email,
            "assigned_branches": self.assigned_branches,
            "assigned_reg_nos": self.assigned_reg_nos,
            "linked_reg_no": self.linked_reg_no,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, doc):
        if not doc:
            return None
        return cls(
            username=doc.get("username", ""),
            password_hash=doc.get("password_hash", ""),
            role=doc.get("role", "Student"),
            full_name=doc.get("full_name", ""),
            email=doc.get("email", ""),
            assigned_branches=doc.get("assigned_branches", []),
            assigned_reg_nos=doc.get("assigned_reg_nos", []),
            linked_reg_no=doc.get("linked_reg_no", ""),
            is_active=doc.get("is_active", True),
            tokens_valid_after=doc.get("tokens_valid_after"),
            created_at=doc.get("created_at"),
            updated_at=doc.get("updated_at"),
        )
