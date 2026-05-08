import React, { useState, useEffect } from "react";

import {
  getStudents,
  addStudent,
  deleteStudent,
  updateStudent
} from "../services/api";

import StudentTable from "../components/StudentTable";

import "./Dashboard.css";


function Dashboard() {

  const [students, setStudents] = useState([]);

  const [form, setForm] = useState({
    reg_no: "",
    roll_no: "",
    name: "",
    age: "",
    branch: ""
  });


  // LOAD STUDENTS ON PAGE LOAD
  useEffect(() => {
    loadStudents();
  }, []);


  // HANDLE INPUT CHANGE
  const handleChange = (e) => {

    setForm({
      ...form,
      [e.target.name]: e.target.value
    });
  };


  // LOAD STUDENTS
  const loadStudents = async () => {

    try {

      const data = await getStudents();

      setStudents(data);

    } catch (error) {

      console.error(error);

      alert("Failed to load students");
    }
  };


  // ADD STUDENT
  const handleAddStudent = async () => {

    if (
      !form.reg_no ||
      !form.roll_no ||
      !form.name ||
      !form.age ||
      !form.branch
    ) {
      alert("Please fill all fields");
      return;
    }

    try {

      const result = await addStudent(form);

      if (result.error) {
        alert(result.error);
        return;
      }

      alert("Student Added Successfully");

      setForm({
        reg_no: "",
        roll_no: "",
        name: "",
        age: "",
        branch: ""
      });

      loadStudents();

    } catch (error) {

      console.error(error);

      alert("Failed to add student");
    }
  };


  // DELETE STUDENT
  const handleDelete = async (reg_no) => {

    try {

      const result = await deleteStudent(reg_no);

      if (result.error) {
        alert(result.error);
        return;
      }

      alert("Student Deleted");

      loadStudents();

    } catch (error) {

      console.error(error);

      alert("Failed to delete student");
    }
  };


  // EDIT STUDENT
  const handleEdit = async (student) => {

    const name = prompt(
      "Enter new name",
      student.name
    );

    const age = prompt(
      "Enter new age",
      student.age
    );

    const branch = prompt(
      "Enter new branch",
      student.branch
    );

    if (!name || !age || !branch) return;

    try {

      const result = await updateStudent(
        student.reg_no,
        {
          ...student,
          name,
          age,
          branch
        }
      );

      if (result.error) {
        alert(result.error);
        return;
      }

      alert("Student Updated");

      loadStudents();

    } catch (error) {

      console.error(error);

      alert("Failed to update student");
    }
  };


  return (

    <div className="dashboard-container">

      <h1 className="dashboard-title">
        Student Management System
      </h1>


      <div className="form-container">

        <input
          name="reg_no"
          placeholder="Registration Number"
          value={form.reg_no}
          onChange={handleChange}
        />

        <input
          name="roll_no"
          placeholder="Roll Number"
          value={form.roll_no}
          onChange={handleChange}
        />

        <input
          name="name"
          placeholder="Student Name"
          value={form.name}
          onChange={handleChange}
        />

        <input
          name="age"
          type="number"
          placeholder="Age"
          value={form.age}
          onChange={handleChange}
        />

        <input
          name="branch"
          placeholder="Branch"
          value={form.branch}
          onChange={handleChange}
        />

        <button
          className="add-btn"
          onClick={handleAddStudent}
        >
          Add Student
        </button>

      </div>


      <button
        className="refresh-btn"
        onClick={loadStudents}
      >
        Refresh Students
      </button>


      <StudentTable
        students={students}
        onEdit={handleEdit}
        onDelete={handleDelete}
      />

    </div>
  );
}

export default Dashboard;