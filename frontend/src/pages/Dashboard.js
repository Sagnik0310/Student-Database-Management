import React, { useState } from "react";
import { getStudents, addStudent, deleteStudent, updateStudent } from "../services/api";
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

  const handleChange = (e) => {
    setForm({
      ...form,
      [e.target.name]: e.target.value
    });
  };

  const loadStudents = async () => {
    const data = await getStudents();
    setStudents(data);
  };

  const handleAddStudent = async () => {

    await addStudent(form);

    alert("Student Added Successfully");

    setForm({
      reg_no: "",
      roll_no: "",
      name: "",
      age: "",
      branch: ""
    });
  };

  const handleDelete = async (reg_no) => {

    await deleteStudent(reg_no);

    alert("Student Deleted");

  };

  const handleEdit = async (student) => {

    const name = prompt("Enter new name", student.name);
    const age = prompt("Enter new age", student.age);
    const branch = prompt("Enter new branch", student.branch);

    if (!name || !age || !branch) return;

    await updateStudent(student.reg_no, {
      ...student,
      name,
      age,
      branch
    });

    alert("Student Updated");

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

      {/* Button to load data only when requested */}

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