import sys
import os

# =========================
# ADD PROJECT ROOT TO PATH
# =========================
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

# =========================
# FLASK APP
# =========================
app = Flask(__name__)

# =========================
# ENABLE CORS
# =========================
CORS(
    app,
    resources={
        r"/*": {
            "origins": "*"
        }
    }
)


# =========================
# HOME ROUTE
# =========================
@app.route("/", methods=["GET"])
def home():

    return jsonify({
        "success": True,
        "message": "Student Management API is running"
    })


# =========================
# HEALTH CHECK
# =========================
@app.route("/health", methods=["GET"])
def health_check():

    return jsonify({
        "success": True,
        "status": "healthy"
    })


# =========================
# GET ALL STUDENTS
# =========================
@app.route("/students", methods=["GET"])
def get_students():

    try:

        students = view_students()

        return jsonify(students), 200

    except Exception as e:

        print("GET STUDENTS ERROR:", str(e))

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# =========================
# GET SINGLE STUDENT
# =========================
@app.route("/students/<reg_no>", methods=["GET"])
def get_student(reg_no):

    try:

        student = search_student(reg_no)

        if not student:

            return jsonify({
                "success": False,
                "message": "Student not found"
            }), 404

        return jsonify(student), 200

    except Exception as e:

        print("GET STUDENT ERROR:", str(e))

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# =========================
# ADD STUDENT
# =========================
@app.route("/students", methods=["POST"])
def create_student():

    try:

        data = request.get_json()

        print("RECEIVED DATA:", data)

        if not data:

            return jsonify({
                "success": False,
                "message": "No JSON data received"
            }), 400

        required_fields = [
            "reg_no",
            "roll_no",
            "name",
            "age",
            "branch"
        ]

        for field in required_fields:

            if field not in data or str(data[field]).strip() == "":

                return jsonify({
                    "success": False,
                    "message": f"{field} is required"
                }), 400

        result = add_student(
            str(data["reg_no"]),
            str(data["roll_no"]),
            str(data["name"]),
            int(data["age"]),
            str(data["branch"])
        )

        print("ADD RESULT:", result)

        if "error" in result:

            return jsonify({
                "success": False,
                "message": result["error"]
            }), 400

        return jsonify({
            "success": True,
            "message": "Student added successfully"
        }), 201

    except Exception as e:

        print("ADD STUDENT ERROR:", str(e))

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# =========================
# UPDATE STUDENT
# =========================
@app.route("/students/<reg_no>", methods=["PUT"])
def update_student_api(reg_no):

    try:

        data = request.get_json()

        print("UPDATE DATA:", data)

        result = update_student(
            reg_no,
            str(data["name"]),
            int(data["age"]),
            str(data["branch"])
        )

        print("UPDATE RESULT:", result)

        if "error" in result:

            return jsonify({
                "success": False,
                "message": result["error"]
            }), 404

        return jsonify({
            "success": True,
            "message": "Student updated successfully"
        }), 200

    except Exception as e:

        print("UPDATE ERROR:", str(e))

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# =========================
# DELETE STUDENT
# =========================
@app.route("/students/<reg_no>", methods=["DELETE"])
def delete_student_api(reg_no):

    try:

        result = delete_student(reg_no)

        print("DELETE RESULT:", result)

        if "error" in result:

            return jsonify({
                "success": False,
                "message": result["error"]
            }), 404

        return jsonify({
            "success": True,
            "message": "Student deleted successfully"
        }), 200

    except Exception as e:

        print("DELETE ERROR:", str(e))

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# =========================
# MAIN
# =========================
if __name__ == "__main__":

    port = int(os.environ.get("PORT", 10000))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=True
    )