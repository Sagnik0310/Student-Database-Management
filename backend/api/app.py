import sys
import os

# Add project root to Python path
sys.path.append(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../")
    )
)

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
    return jsonify({
        "message": "Student Management API running"
    })


# GET ALL STUDENTS
@app.route("/students", methods=["GET"])
def get_students():

    try:

        data = view_students()

        return jsonify(data)

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


# GET ONE STUDENT
@app.route("/students/<reg_no>", methods=["GET"])
def get_student(reg_no):

    try:

        data = search_student(reg_no)

        if not data:
            return jsonify({
                "error": "Student not found"
            }), 404

        return jsonify(data)

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


# CREATE STUDENT
@app.route("/students", methods=["POST"])
def create_student():

    try:

        data = request.get_json()

        result = add_student(
            data["reg_no"],
            data["roll_no"],
            data["name"],
            int(data["age"]),
            data["branch"]
        )

        if "error" in result:
            return jsonify(result), 400

        return jsonify(result), 201

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


# UPDATE STUDENT
@app.route("/students/<reg_no>", methods=["PUT"])
def update_student_api(reg_no):

    try:

        data = request.get_json()

        result = update_student(
            reg_no,
            data["name"],
            int(data["age"]),
            data["branch"]
        )

        if "error" in result:
            return jsonify(result), 404

        return jsonify({
            "success": True,
            "message": "Student updated successfully"
        })

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


# DELETE STUDENT
@app.route("/students/<reg_no>", methods=["DELETE"])
def delete_student_api(reg_no):

    try:

        result = delete_student(reg_no)

        if "error" in result:
            return jsonify(result), 404

        return jsonify({
            "success": True,
            "message": "Student deleted successfully"
        })

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


if __name__ == "__main__":

    port = int(os.environ.get("PORT", 10000))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=True
    )