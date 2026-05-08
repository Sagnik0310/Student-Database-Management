from database.db_connection import get_connection
import re

db = get_connection()

if db is None:
    print("Database connection failed. App will still run.")
    students_collection = None
else:
    students_collection = db["students"]


def add_student(reg_no, roll_no, name, age, branch):

    if students_collection is None:
        return {"error": "Database not connected"}

    if not reg_no.strip():
        return {"error": "Registration number cannot be empty"}

    if not roll_no.strip():
        return {"error": "Roll number cannot be empty"}

    if not name.strip():
        return {"error": "Name cannot be empty"}

    if age <= 0:
        return {"error": "Age must be greater than 0"}

    if not branch.strip():
        return {"error": "Branch cannot be empty"}

    if not re.match(r'^[A-Za-z0-9]+$', reg_no):
        return {"error": "Registration number must be alphanumeric"}

    existing_student = students_collection.find_one({"reg_no": reg_no})

    if existing_student:
        return {"error": "Student already exists"}

    student_data = {
        "reg_no": reg_no,
        "roll_no": roll_no,
        "name": name,
        "age": age,
        "branch": branch
    }

    try:
        students_collection.insert_one(student_data)

        return {
            "success": True,
            "message": "Student added successfully"
        }

    except Exception as e:
        return {"error": str(e)}


def view_students():

    if students_collection is None:
        return []

    try:
        result = students_collection.find()

        students = []

        for student in result:

            students.append({
                "reg_no": student.get("reg_no"),
                "roll_no": student.get("roll_no"),
                "name": student.get("name"),
                "age": student.get("age"),
                "branch": student.get("branch")
            })

        return students

    except Exception:
        return []


def search_student(reg_no):

    if students_collection is None:
        return None

    try:
        student = students_collection.find_one({"reg_no": reg_no})

        if not student:
            return None

        return {
            "reg_no": student.get("reg_no"),
            "roll_no": student.get("roll_no"),
            "name": student.get("name"),
            "age": student.get("age"),
            "branch": student.get("branch")
        }

    except Exception:
        return None


def update_student(reg_no, name, age, branch):

    if students_collection is None:
        return {"error": "Database not connected"}

    try:

        updated_data = {
            "$set": {
                "name": name,
                "age": age,
                "branch": branch
            }
        }

        result = students_collection.update_one(
            {"reg_no": reg_no},
            updated_data
        )

        if result.matched_count == 0:
            return {"error": "Student not found"}

        return {"success": True}

    except Exception as e:
        return {"error": str(e)}


def delete_student(reg_no):

    if students_collection is None:
        return {"error": "Database not connected"}

    try:

        result = students_collection.delete_one(
            {"reg_no": reg_no}
        )

        if result.deleted_count == 0:
            return {"error": "Student not found"}

        return {"success": True}

    except Exception as e:
        return {"error": str(e)}