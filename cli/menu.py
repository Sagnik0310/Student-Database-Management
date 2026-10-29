import sys
import getpass
from services.student_service import (
    add_student,
    view_students,
    search_student,
    update_student,
    delete_student,
)
from services.auth_service import (
    authenticate_user,
    can_access_student,
    filter_students_for_user,
    can_modify_student,
    log_audit_event,
)
from logs.logger import logger


def _read_password(prompt_text="Password: "):
    """Read password securely from terminal, falling back to standard input if non-interactive."""
    if sys.stdin and sys.stdin.isatty():
        try:
            return getpass.getpass(prompt_text).strip()
        except Exception:
            pass
    return input(prompt_text).strip()


def cli_login(max_attempts=3):
    """Prompt the CLI operator to authenticate and return the verified user dictionary."""
    print("\n" + "=" * 40)
    print("   STUDENT DB — AUTHENTICATION REQUIRED")
    print("=" * 40)

    for attempt in range(1, max_attempts + 1):
        username = input("Username: ").strip()
        password = _read_password("Password: ")

        res = authenticate_user(username, password, ip_address="cli-local")
        if "error" not in res and res.get("user"):
            user = res["user"]
            print(
                f"\n✅ Welcome, {user.get('full_name')} "
                f"[Role: {user.get('role')}]"
            )
            return user

        remaining = max_attempts - attempt
        print(
            f"❌ {res.get('error', 'Authentication failed')} "
            f"({remaining} attempt(s) remaining)"
        )

    print("🚫 Maximum login attempts exceeded. Exiting.")
    logger.warning("CLI exited due to failed login attempts")
    return None


def menu(current_user=None):
    if current_user is None:
        current_user = cli_login()
        if not current_user:
            return

    role = current_user.get("role", "Student")

    while True:
        try:
            print("\n" + "=" * 40)
            print(f"     STUDENT MANAGEMENT SYSTEM ({role})")
            print("=" * 40)

            print("1️⃣  Add Student")
            print("2️⃣  View Students")
            print("3️⃣  Search Student")
            print("4️⃣  Update Student")
            print("5️⃣  Delete Student")
            print("6️⃣  Exit")

            print("-" * 40)

            choice = input("Enter your choice: ").strip()

            # ADD STUDENT (Admin only)
            if choice == "1":
                if role != "Admin":
                    print("❌ Access denied: Only Admin users can add students.")
                    continue

                print("\nAdd New Student\n")

                reg_no = input("Registration Number: ").strip()
                roll_no = input("Roll Number: ").strip()
                name = input("Student Name: ").strip()

                try:
                    age = int(input("Age: "))
                except ValueError:
                    print("Age must be a number")
                    continue

                branch = input("Branch: ").strip()

                result = add_student(
                    reg_no,
                    roll_no,
                    name,
                    age,
                    branch,
                )

                if "error" in result:
                    print(f"❌ {result['error']}")
                else:
                    log_audit_event(
                        "CLI_STUDENT_ADDED",
                        current_user.get("username"),
                        role,
                        f"Added student {reg_no} via CLI",
                    )
                    print(f"✅ {result['message']}")

            # VIEW STUDENTS (Filtered by RBAC)
            elif choice == "2":
                all_students = view_students()
                students = filter_students_for_user(current_user, all_students)

                if not students:
                    print("No students found")
                else:
                    print("\nStudent Records\n")
                    for student in students:
                        print(
                            f"Reg: {student['reg_no']} | "
                            f"Roll: {student['roll_no']} | "
                            f"Name: {student['name']} | "
                            f"Age: {student['age']} | "
                            f"Branch: {student['branch']}"
                        )

            # SEARCH STUDENT (RBAC enforced)
            elif choice == "3":
                reg_no = input("Enter registration number: ").strip()

                if not reg_no:
                    print("Registration number cannot be empty")
                    continue

                if (
                    role == "Student"
                    and reg_no != str(current_user.get("linked_reg_no") or "").strip()
                ):
                    print("❌ Access denied: You can only view your own student record.")
                    continue

                student = search_student(reg_no)

                if not student:
                    print("❌ Student not found")
                elif not can_access_student(current_user, student):
                    print("❌ Access denied: You are not assigned to this student.")
                else:
                    print("\nStudent Found\n")
                    print(
                        f"Reg: {student['reg_no']} | "
                        f"Roll: {student['roll_no']} | "
                        f"Name: {student['name']} | "
                        f"Age: {student['age']} | "
                        f"Branch: {student['branch']}"
                    )

            # UPDATE STUDENT (Admin and authorized Faculty)
            elif choice == "4":
                if role not in ("Admin", "Faculty"):
                    print("❌ Access denied: Students cannot modify records.")
                    continue

                reg_no = input("Registration number to update: ").strip()
                existing = search_student(reg_no)
                if not existing:
                    print("❌ Student not found")
                    continue

                if not can_modify_student(current_user, existing):
                    print("❌ Access denied: You are not authorized to update this student.")
                    continue

                name = input("New name: ").strip()

                try:
                    age = int(input("New age: "))
                except ValueError:
                    print("Age must be a number")
                    continue

                branch = input("New branch: ").strip()

                result = update_student(
                    reg_no,
                    name,
                    age,
                    branch,
                )

                if "error" in result:
                    print(f"❌ {result['error']}")
                else:
                    log_audit_event(
                        "CLI_STUDENT_UPDATED",
                        current_user.get("username"),
                        role,
                        f"Updated student {reg_no} via CLI",
                    )
                    print("✅ Student updated successfully")

            # DELETE STUDENT (Admin only)
            elif choice == "5":
                if role != "Admin":
                    print("❌ Access denied: Only Admin users can delete students.")
                    continue

                reg_no = input("Registration number to delete: ").strip()

                result = delete_student(reg_no)

                if "error" in result:
                    print(f"❌ {result['error']}")
                else:
                    log_audit_event(
                        "CLI_STUDENT_DELETED",
                        current_user.get("username"),
                        role,
                        f"Deleted student {reg_no} via CLI",
                    )
                    print("✅ Student deleted successfully")

            # EXIT
            elif choice == "6":
                print("\nExiting program...")
                logger.info(f"Program exited by user {current_user.get('username')}")
                break

            else:
                print("Invalid choice. Please try again.")

        except KeyboardInterrupt:
            print("\nProgram interrupted by user")
            logger.warning("Program interrupted by user")
            break

        except Exception as e:
            print("Unexpected error occurred")
            logger.error(f"Menu error: {e}")
