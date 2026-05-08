const API = "https://student-database-management-l3pl.onrender.com";

// GET ALL STUDENTS
export const getStudents = async () => {

  const response = await fetch(`${API}/students`);

  if (!response.ok) {
    throw new Error("Failed to fetch students");
  }

  return response.json();
};


// ADD STUDENT
export const addStudent = async (student) => {

  const response = await fetch(`${API}/students`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      reg_no: student.reg_no,
      roll_no: student.roll_no,
      name: student.name,
      age: Number(student.age),
      branch: student.branch,
    }),
  });

  const data = await response.json();

  if (!response.ok) {
    console.error(data);
    throw new Error(data.error || "Failed to add student");
  }

  return data;
};


// DELETE STUDENT
export const deleteStudent = async (reg_no) => {

  const response = await fetch(`${API}/students/${reg_no}`, {
    method: "DELETE",
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.error || "Failed to delete student");
  }

  return data;
};


// UPDATE STUDENT
export const updateStudent = async (reg_no, student) => {

  const response = await fetch(`${API}/students/${reg_no}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      name: student.name,
      age: Number(student.age),
      branch: student.branch,
    }),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.error || "Failed to update student");
  }

  return data;
};


// SEARCH STUDENT
export const searchStudent = async (reg_no) => {

  const response = await fetch(`${API}/students/${reg_no}`);

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.error || "Student not found");
  }

  return data;
};