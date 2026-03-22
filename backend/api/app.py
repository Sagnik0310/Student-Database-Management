import sys
import os

# Add project root to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from flask import Flask, request, jsonify
from flask_cors import CORS

from services.student_service import (
    add_student,
    view_students,
    search_student,
    update_student,
    delete_student
)

app = Flask(__name__)
CORS(app)


@app.route("/")
def home():
    return jsonify({"message": "Student Management API running"})


# GET ALL STUDENTS
@app.route("/students", methods=["GET"])
def get_students():
    try:
        data = view_students()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# GET ONE STUDENT
@app.route("/students/<reg_no>", methods=["GET"])
def get_student(reg_no):
    try:
        data = search_student(reg_no)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# CREATE STUDENT
@app.route("/students", methods=["POST"])
def create_student():
    data = request.get_json()

    try:
        add_student(
            data["reg_no"],
            data["roll_no"],
            data["name"],
            int(data["age"]),
            data["branch"]
        )

        return jsonify({
            "success": True,
            "message": "Student added successfully"
        })

    except ValueError as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 400


# UPDATE STUDENT
@app.route("/students/<reg_no>", methods=["PUT"])
def update_student_api(reg_no):
    try:
        data = request.get_json()

        update_student(
            reg_no,
            data["name"],
            int(data["age"]),
            data["branch"]
        )

        return jsonify({"message": "Student updated successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# DELETE STUDENT
@app.route("/students/<reg_no>", methods=["DELETE"])
def delete_student_api(reg_no):
    try:
        delete_student(reg_no)
        return jsonify({"message": "Student deleted successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500



if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)