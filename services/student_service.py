import mysql.connector as mc
from database.db_connection import get_connection
import re

db = get_connection()

if db is None:
    print("Database connection failed. App will still run.")
    cursor = None
else:
    cursor = db.cursor()


def add_student(reg_no, roll_no, name, age, branch):

    if cursor is None:
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

    query = "INSERT INTO students(reg_no, roll_no, name, age, branch) VALUES (%s,%s,%s,%s,%s)"
    values = (reg_no, roll_no, name, age, branch)

    try:
        cursor.execute(query, values)
        db.commit()
        return {"success": True, "message": "Student added successfully"}

    except mc.IntegrityError:
        return {"error": "Student already exists"}

    except mc.Error as e:
        return {"error": str(e)}


def view_students():

    if cursor is None:
        return []

    try:
        cursor.execute("SELECT * FROM students")
        result = cursor.fetchall()

        students = []
        for row in result:
            students.append({
                "reg_no": row[0],
                "roll_no": row[1],
                "name": row[2],
                "age": row[3],
                "branch": row[4]
            })

        return students

    except Exception:
        return []


def search_student(reg_no):

    if cursor is None:
        return None

    try:
        query = "SELECT * FROM students WHERE reg_no = %s"
        cursor.execute(query, (reg_no,))
        result = cursor.fetchone()

        if not result:
            return None

        return {
            "reg_no": result[0],
            "roll_no": result[1],
            "name": result[2],
            "age": result[3],
            "branch": result[4]
        }

    except Exception:
        return None


def update_student(reg_no, name, age, branch):

    if cursor is None:
        return {"error": "Database not connected"}

    try:
        query = "UPDATE students SET name=%s, age=%s, branch=%s WHERE reg_no=%s"
        values = (name, age, branch, reg_no)

        cursor.execute(query, values)
        db.commit()

        if cursor.rowcount == 0:
            return {"error": "Student not found"}

        return {"success": True}

    except mc.Error as e:
        return {"error": str(e)}


def delete_student(reg_no):

    if cursor is None:
        return {"error": "Database not connected"}

    try:
        query = "DELETE FROM students WHERE reg_no = %s"

        cursor.execute(query, (reg_no,))
        db.commit()

        if cursor.rowcount == 0:
            return {"error": "Student not found"}

        return {"success": True}

    except mc.Error as e:
        return {"error": str(e)}