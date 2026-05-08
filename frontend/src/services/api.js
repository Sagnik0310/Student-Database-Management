const API = "http://127.0.0.1:10000";

// GET ALL STUDENTS
export const getStudents = async () => {

  const response = await fetch(`${API}/students`);

  if (!response.ok) {
    throw new Error("Failed to fetch students");
  }

  return response.json();
};


// ADD STUDENT
export const addStudent = async (data) => {

  const response = await fetch(`${API}/students`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(data)
  });

  return response.json();
};


// DELETE STUDENT
export const deleteStudent = async (reg_no) => {

  const response = await fetch(`${API}/students/${reg_no}`, {
    method: "DELETE"
  });

  return response.json();
};


// UPDATE STUDENT
export const updateStudent = async (reg_no, data) => {

  const response = await fetch(`${API}/students/${reg_no}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(data)
  });

  return response.json();
};


// SEARCH STUDENT
export const searchStudent = async (reg_no) => {

  const response = await fetch(`${API}/students/${reg_no}`);

  return response.json();
};