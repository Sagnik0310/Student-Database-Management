import mysql.connector as mc
from database.db_connection import get_connection
from models.student import student
from logs.logger import logger
import re
from tabulate import tabulate

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

    # Example reg_no format validation
    if not re.match(r'^[A-Za-z0-9]+$', reg_no):
        print("Registration number must be alphanumeric")
        return

    query = "INSERT INTO students(reg_no, roll_no, name, age, branch) VALUES (%s,%s,%s,%s,%s)"
    values = (reg_no, roll_no, name, age, branch)

    try:
        cursor.execute(query, values)
        db.commit()

        print("Student added successfully")
        logger.info(f"Student added: {reg_no}")

    except mc.IntegrityError:
        print("Student with this registration number already exists")
        logger.warning(f"Duplicate student insertion attempt: {reg_no}")

    except mc.Error as e:
        print("Database error occurred while adding student")
        logger.error(f"MySQL error while adding student {reg_no}: {e}")

    except Exception as e:
        print("Unexpected error occurred")
        logger.error(f"Unexpected error while adding student {reg_no}: {e}")


def view_students():

    try:
        cursor.execute("SELECT * FROM students")
        result = cursor.fetchall()

        if not result:
            print("No students found")
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

            # CLI output
            print(f"Reg No: {row[0]}, Roll No: {row[1]}, Name: {row[2]}, Age: {row[3]}, Branch: {row[4]}")

        return students

    except Exception as e:
        print("Error retrieving students")
        logger.error(f"Error viewing students: {e}")
        return []


def search_student(reg_no):

    try:
        query = "SELECT * FROM students WHERE reg_no = %s"
        cursor.execute(query, (reg_no,))
        result = cursor.fetchone()

        if not result:
            print("Student not found")
            logger.warning(f"Search attempted but student not found: {reg_no}")
            return None

        student_data = {
            "reg_no": result[0],
            "roll_no": result[1],
            "name": result[2],
            "age": result[3],
            "branch": result[4]
        }

        # CLI output
        print("\nStudent Found:")
        print(f"Reg No : {result[0]}")
        print(f"Roll No: {result[1]}")
        print(f"Name   : {result[2]}")
        print(f"Age    : {result[3]}")
        print(f"Branch : {result[4]}")

        logger.info(f"Student searched: {reg_no}")

        return student_data

    except Exception as e:
        print("Error searching student")
        logger.error(f"Error searching student {reg_no}: {e}")
        return None


def update_student(reg_no, name, age, branch):

    try:
        query = "UPDATE students SET name=%s, age=%s, branch=%s WHERE reg_no=%s"
        values = (name, age, branch, reg_no)

        cursor.execute(query, values)
        db.commit()

        if cursor.rowcount == 0:
            print("Student not found")
            logger.warning(f"Update attempted but student not found: {reg_no}")
        else:
            print("Student updated successfully")
            logger.info(f"Student updated: {reg_no}")

    except mc.Error as e:
        print("Database error occurred while updating student")
        logger.error(f"MySQL error while updating student {reg_no}: {e}")

    except Exception as e:
        print("Unexpected error occurred")
        logger.error(f"Unexpected error while updating student {reg_no}: {e}")


def delete_student(reg_no):

    try:
        query = "DELETE FROM students WHERE reg_no = %s"

        cursor.execute(query, (reg_no,))
        db.commit()

        if cursor.rowcount == 0:
            print("Student not found")
            logger.warning(f"Delete attempted but student not found: {reg_no}")
        else:
            print("Student deleted successfully")
            logger.info(f"Student deleted: {reg_no}")

    except mc.Error as e:
        print("Database error occurred while deleting student")
        logger.error(f"MySQL error while deleting student {reg_no}: {e}")

    except Exception as e:
        print("Unexpected error occurred")
        logger.error(f"Unexpected error while deleting student {reg_no}: {e}")