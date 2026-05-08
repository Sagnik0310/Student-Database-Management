import React, { useState } from "react";

import {
  getStudents,
  addStudent,
  deleteStudent,
  updateStudent
} from "../services/api";

import StudentTable from "../components/StudentTable";


function Dashboard() {

  const [students, setStudents] = useState([]);

  const [form, setForm] = useState({
    reg_no: "",
    roll_no: "",
    name: "",
    age: "",
    branch: ""
  });


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

      // RELOAD TABLE
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

      // RELOAD TABLE
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

      // RELOAD TABLE
      loadStudents();

    } catch (error) {

      console.error(error);

      alert("Failed to update student");
    }
  };


  return (

    <div>

      <h1>Student Dashboard</h1>

      <div className="add-student">

        <input
          name="reg_no"
          placeholder="Reg No"
          value={form.reg_no}
          onChange={handleChange}
        />

        <input
          name="roll_no"
          placeholder="Roll No"
          value={form.roll_no}
          onChange={handleChange}
        />

        <input
          name="name"
          placeholder="Name"
          value={form.name}
          onChange={handleChange}
        />

        <input
          name="age"
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

        <button onClick={handleAddStudent}>
          Add Student
        </button>

      </div>


      <button onClick={loadStudents}>
        Show Students
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