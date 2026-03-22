import mysql.connector as mc
from database.db_connection import get_connection
from models.student import student
import re

db = get_connection()

if db is None:
    print("Database connection failed. Exiting.")
    exit()

cursor = db.cursor()


def add_student(reg_no, roll_no, name, age, branch):

    # -------- INPUT VALIDATION --------

    if not reg_no.strip():
        print("Registration number cannot be empty")
        return

    if not roll_no.strip():
        print("Roll number cannot be empty")
        return

    if not name.strip():
        print("Name cannot be empty")
        return

    if age <= 0:
        print("Age must be greater than 0")
        return

    if not branch.strip():
        print("Branch cannot be empty")
        return

    if not re.match(r'^[A-Za-z0-9]+$', reg_no):
        print("Registration number must be alphanumeric")
        return

    query = "INSERT INTO students(reg_no, roll_no, name, age, branch) VALUES (%s,%s,%s,%s,%s)"
    values = (reg_no, roll_no, name, age, branch)

    try:
        cursor.execute(query, values)
        db.commit()
        print("Student added successfully")

    except mc.IntegrityError:
        print("Student with this registration number already exists")

    except mc.Error as e:
        print(f"MySQL error: {e}")

    except Exception as e:
        print(f"Unexpected error: {e}")


def view_students():
    try:
        cursor.execute("SELECT * FROM students")
        result = cursor.fetchall()

        if not result:
            return []

        students = []

        for row in result:
            student_data = {
                "reg_no": row[0],
                "roll_no": row[1],
                "name": row[2],
                "age": row[3],
                "branch": row[4]
            }
            students.append(student_data)

        return students

    except Exception as e:
        print(f"Error retrieving students: {e}")
        return []


def search_student(reg_no):
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

    except Exception as e:
        print(f"Error searching student: {e}")
        return None


def update_student(reg_no, name, age, branch):
    try:
        query = "UPDATE students SET name=%s, age=%s, branch=%s WHERE reg_no=%s"
        values = (name, age, branch, reg_no)

        cursor.execute(query, values)
        db.commit()

        if cursor.rowcount == 0:
            print("Student not found")
        else:
            print("Student updated successfully")

    except mc.Error as e:
        print(f"MySQL error: {e}")

    except Exception as e:
        print(f"Unexpected error: {e}")


def delete_student(reg_no):
    try:
        query = "DELETE FROM students WHERE reg_no = %s"

        cursor.execute(query, (reg_no,))
        db.commit()

        if cursor.rowcount == 0:
            print("Student not found")
        else:
            print("Student deleted successfully")

    except mc.Error as e:
        print(f"MySQL error: {e}")

    except Exception as e:
        print(f"Unexpected error: {e}")