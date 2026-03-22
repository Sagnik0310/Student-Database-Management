const API = "http://127.0.0.1:5000";

export const getStudents = () =>
  fetch(`${API}/students`).then(res => res.json());

export const addStudent = (data) =>
  fetch(`${API}/students`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data)
  }).then(res => res.json());

export const deleteStudent = (reg_no) =>
  fetch(`${API}/students/${reg_no}`, {
    method: "DELETE"
  }).then(res => res.json());

export const updateStudent = (reg_no, data) =>
  fetch(`${API}/students/${reg_no}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data)
  }).then(res => res.json());

export const searchStudent = (reg_no) =>
  fetch(`${API}/students/${reg_no}`).then(res => res.json());