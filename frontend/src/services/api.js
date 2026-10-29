export const API =
  (typeof import.meta !== "undefined" && import.meta.env && import.meta.env.VITE_API_URL) ||
  (typeof process !== "undefined" && process.env && (process.env.VITE_API_URL || process.env.REACT_APP_API_URL)) ||
  "https://student-database-management-l3pl.onrender.com";

const ENRICHMENT_STORAGE_KEY = "studentdb_v2_extended_fields";
const ACTIVITY_STORAGE_KEY = "studentdb_v2_activity_logs";

// ==========================================
// IN-MEMORY AUTHENTICATION STATE (NEVER STORED IN LOCALSTORAGE)
// ==========================================
let _currentUser = null;
let _csrfToken = "";
let _memorySessionToken = "";
const _authListeners = new Set();

export const subscribeAuthChange = (listener) => {
  _authListeners.add(listener);
  return () => _authListeners.delete(listener);
};

const notifyAuthChange = () => {
  _authListeners.forEach((fn) => {
    try {
      fn(_currentUser);
    } catch {
      // ignore listener errors
    }
  });
};

export const getCurrentUser = () => _currentUser;
export const getCsrfToken = () => _csrfToken;

export const setAuthSession = (user, csrfToken = "", sessionToken = "") => {
  _currentUser = user || null;
  _csrfToken = csrfToken || "";
  _memorySessionToken = sessionToken || "";
  notifyAuthChange();
};

export const clearAuthSession = () => {
  _currentUser = null;
  _csrfToken = "";
  _memorySessionToken = "";
  notifyAuthChange();
};

const buildHeaders = (method = "GET", extraHeaders = {}) => {
  const headers = { ...extraHeaders };
  if (["POST", "PUT", "DELETE", "PATCH"].includes(method.toUpperCase())) {
    if (_csrfToken) {
      headers["X-CSRF-Token"] = _csrfToken;
    }
  }
  if (_memorySessionToken) {
    headers["Authorization"] = `Bearer ${_memorySessionToken}`;
  }
  return headers;
};

const apiFetch = async (path, options = {}) => {
  const method = (options.method || "GET").toUpperCase();
  const headers = buildHeaders(method, options.headers || {});
  const response = await fetch(`${API}${path}`, {
    ...options,
    method,
    credentials: "include",
    headers,
  });

  if (response.status === 401 && !path.includes("/auth/login")) {
    clearAuthSession();
  }

  return response;
};

// Helper to persist extended optional fields locally if a legacy backend strips them
const getEnrichmentMap = () => {
  try {
    const raw = localStorage.getItem(ENRICHMENT_STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
};

const saveEnrichment = (reg_no, extra) => {
  if (!reg_no) return;
  try {
    const map = getEnrichmentMap();
    map[reg_no] = {
      ...(map[reg_no] || {}),
      ...extra,
      updated_at: new Date().toISOString(),
    };
    localStorage.setItem(ENRICHMENT_STORAGE_KEY, JSON.stringify(map));
  } catch {
    // Ignore storage quota errors
  }
};

const removeEnrichment = (reg_no) => {
  if (!reg_no) return;
  try {
    const map = getEnrichmentMap();
    delete map[reg_no];
    localStorage.setItem(ENRICHMENT_STORAGE_KEY, JSON.stringify(map));
  } catch {
    // Ignore storage errors
  }
};

export const mergeStudentRecord = (s) => {
  if (!s) return s;
  const map = getEnrichmentMap();
  const localExtra = map[s.reg_no] || {};
  return {
    reg_no: String(s.reg_no ?? ""),
    roll_no: String(s.roll_no ?? ""),
    name: String(s.name ?? ""),
    age: Number(s.age ?? 0),
    branch: String(s.branch ?? ""),
    email: s.email || localExtra.email || "",
    phone: s.phone || localExtra.phone || "",
    semester: s.semester || localExtra.semester || "",
    academic_year: s.academic_year || localExtra.academic_year || "2025-2026",
    admission_date: s.admission_date || localExtra.admission_date || "",
    status: s.status || localExtra.status || "Active",
    gpa:
      s.gpa !== undefined && s.gpa !== null && s.gpa !== ""
        ? Number(s.gpa)
        : localExtra.gpa !== undefined &&
          localExtra.gpa !== null &&
          localExtra.gpa !== ""
        ? Number(localExtra.gpa)
        : null,
    attendance_pct:
      s.attendance_pct !== undefined &&
      s.attendance_pct !== null &&
      s.attendance_pct !== ""
        ? Number(s.attendance_pct)
        : localExtra.attendance_pct !== undefined &&
          localExtra.attendance_pct !== null &&
          localExtra.attendance_pct !== ""
        ? Number(localExtra.attendance_pct)
        : null,
    created_at: s.created_at || localExtra.created_at || null,
    updated_at: s.updated_at || localExtra.updated_at || null,
  };
};

// Activity log persistence for audit visibility
export const getActivityLogs = () => {
  try {
    const raw = localStorage.getItem(ACTIVITY_STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
};

export const recordActivityLog = (action, details, type = "info") => {
  try {
    const logs = getActivityLogs();
    const entry = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
      action,
      details,
      type,
      actor: _currentUser?.username || "Administrator",
      role: _currentUser?.role || "Admin",
      timestamp: new Date().toISOString(),
    };
    const updated = [entry, ...logs].slice(0, 100);
    localStorage.setItem(ACTIVITY_STORAGE_KEY, JSON.stringify(updated));
    return entry;
  } catch {
    return null;
  }
};

export const clearActivityLogs = () => {
  try {
    localStorage.removeItem(ACTIVITY_STORAGE_KEY);
  } catch {
    // ignore
  }
};

const extractErrorMessage = (data, fallback) => {
  if (!data) return fallback;
  return data.message || data.error || fallback;
};

// ==========================================
// AUTHENTICATION & USER MANAGEMENT API
// ==========================================
export const loginUser = async (username, password) => {
  const response = await apiFetch("/api/v1/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(extractErrorMessage(data, "Authentication failed"));
  }

  setAuthSession(data.user, data.csrf_token, data.session_token);
  recordActivityLog(
    "User Signed In",
    `Authenticated as ${data.user.username} (${data.user.role})`,
    "success"
  );
  return data;
};

export const logoutUser = async () => {
  try {
    await apiFetch("/api/v1/auth/logout", {
      method: "POST",
    });
  } catch {
    // Proceed with local session cleanup even if network fails
  } finally {
    clearAuthSession();
  }
};

export const fetchCurrentUser = async () => {
  const response = await apiFetch("/api/v1/auth/me", {
    method: "GET",
  });
  if (!response.ok) {
    clearAuthSession();
    return null;
  }
  const data = await response.json().catch(() => ({}));
  if (data && data.user) {
    setAuthSession(data.user, data.csrf_token, _memorySessionToken);
    return data.user;
  }
  return null;
};

export const resetPassword = async ({
  username,
  current_password,
  new_password,
}) => {
  const response = await apiFetch("/api/v1/auth/reset-password", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, current_password, new_password }),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(extractErrorMessage(data, "Failed to update password"));
  }
  return data;
};

export const fetchPlatformUsers = async () => {
  const response = await apiFetch("/api/v1/users", { method: "GET" });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(extractErrorMessage(data, "Failed to load users"));
  }
  return data.users || [];
};

export const createPlatformUser = async (userPayload) => {
  const response = await apiFetch("/api/v1/users", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(userPayload),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(extractErrorMessage(data, "Failed to create user"));
  }
  recordActivityLog(
    "User Created",
    `Created account '${userPayload.username}' with role ${userPayload.role}`,
    "success"
  );
  return data;
};

export const fetchServerAuditLogs = async () => {
  const response = await apiFetch("/api/v1/logs", { method: "GET" });
  if (!response.ok) {
    return getActivityLogs();
  }
  const data = await response.json().catch(() => ({}));
  return Array.isArray(data.logs) ? data.logs : getActivityLogs();
};

// CHECK API HEALTH
export const checkHealth = async () => {
  const response = await apiFetch("/health", { method: "GET" });
  if (!response.ok) {
    throw new Error("Backend health check failed");
  }
  return response.json();
};

// GET ALL STUDENTS
export const getStudents = async () => {
  const response = await apiFetch("/students", { method: "GET" });

  if (!response.ok) {
    let data = null;
    try {
      data = await response.json();
    } catch {
      // ignore
    }
    const err = new Error(extractErrorMessage(data, "Failed to fetch students"));
    err.status = response.status;
    throw err;
  }

  const raw = await response.json();
  const list = Array.isArray(raw) ? raw : Array.isArray(raw?.data) ? raw.data : [];
  return list.map(mergeStudentRecord);
};

// ADD STUDENT
export const addStudent = async (student) => {
  const payload = {
    reg_no: String(student.reg_no || "").trim(),
    roll_no: String(student.roll_no || "").trim(),
    name: String(student.name || "").trim(),
    age: Number(student.age),
    branch: String(student.branch || "").trim(),
    email: String(student.email || "").trim(),
    phone: String(student.phone || "").trim(),
    semester: String(student.semester || "").trim(),
    academic_year: String(student.academic_year || "2025-2026").trim(),
    admission_date: String(student.admission_date || "").trim(),
    status: student.status || "Active",
    gpa:
      student.gpa !== "" && student.gpa !== null && student.gpa !== undefined
        ? Number(student.gpa)
        : null,
    attendance_pct:
      student.attendance_pct !== "" &&
      student.attendance_pct !== null &&
      student.attendance_pct !== undefined
        ? Number(student.attendance_pct)
        : null,
  };

  const response = await apiFetch("/students", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(extractErrorMessage(data, "Failed to add student"));
  }

  saveEnrichment(payload.reg_no, {
    email: payload.email,
    phone: payload.phone,
    semester: payload.semester,
    academic_year: payload.academic_year,
    admission_date: payload.admission_date,
    status: payload.status,
    gpa: payload.gpa,
    attendance_pct: payload.attendance_pct,
    created_at: new Date().toISOString(),
  });

  recordActivityLog(
    "Student Created",
    `Added ${payload.name} (${payload.reg_no}) in ${payload.branch}`,
    "success"
  );

  return data;
};

// DELETE STUDENT
export const deleteStudent = async (reg_no) => {
  const response = await apiFetch(
    `/students/${encodeURIComponent(reg_no)}`,
    {
      method: "DELETE",
    }
  );

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(extractErrorMessage(data, "Failed to delete student"));
  }

  removeEnrichment(reg_no);
  recordActivityLog(
    "Student Deleted",
    `Removed student record with Reg No: ${reg_no}`,
    "warning"
  );

  return data;
};

// UPDATE STUDENT
export const updateStudent = async (reg_no, student) => {
  const payload = {
    roll_no: String(student.roll_no || "").trim(),
    name: String(student.name || "").trim(),
    age: Number(student.age),
    branch: String(student.branch || "").trim(),
    email: String(student.email || "").trim(),
    phone: String(student.phone || "").trim(),
    semester: String(student.semester || "").trim(),
    academic_year: String(student.academic_year || "2025-2026").trim(),
    admission_date: String(student.admission_date || "").trim(),
    status: student.status || "Active",
    gpa:
      student.gpa !== "" && student.gpa !== null && student.gpa !== undefined
        ? Number(student.gpa)
        : null,
    attendance_pct:
      student.attendance_pct !== "" &&
      student.attendance_pct !== null &&
      student.attendance_pct !== undefined
        ? Number(student.attendance_pct)
        : null,
  };

  const response = await apiFetch(
    `/students/${encodeURIComponent(reg_no)}`,
    {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    }
  );

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(extractErrorMessage(data, "Failed to update student"));
  }

  saveEnrichment(reg_no, payload);
  recordActivityLog(
    "Student Updated",
    `Updated ${payload.name} (${reg_no}) — Branch: ${payload.branch}`,
    "info"
  );

  return data;
};

// SEARCH STUDENT BY REG NO
export const searchStudent = async (reg_no) => {
  const response = await apiFetch(
    `/students/${encodeURIComponent(reg_no)}`,
    { method: "GET" }
  );

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(extractErrorMessage(data, "Student not found"));
  }

  return mergeStudentRecord(data);
};

// BULK DELETE STUDENTS (with fallback for legacy backend)
export const bulkDeleteStudents = async (regNos) => {
  if (!Array.isArray(regNos) || regNos.length === 0) {
    throw new Error("No students selected for deletion");
  }

  try {
    const response = await apiFetch("/students/bulk-delete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reg_nos: regNos }),
    });

    if (response.status !== 404 && response.status !== 405) {
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(extractErrorMessage(data, "Bulk deletion failed"));
      }
      regNos.forEach(removeEnrichment);
      recordActivityLog(
        "Bulk Delete",
        `Deleted ${regNos.length} student record(s)`,
        "warning"
      );
      return data;
    }
  } catch (err) {
    if (err.message && err.message.includes("Access denied")) {
      throw err;
    }
  }

  let deletedCount = 0;
  for (const regNo of regNos) {
    try {
      await deleteStudent(regNo);
      deletedCount += 1;
    } catch {
      // continue
    }
  }

  return {
    success: true,
    deleted_count: deletedCount,
    message: `Deleted ${deletedCount} of ${regNos.length} student(s)`,
  };
};

// BULK IMPORT STUDENTS (with fallback for legacy backend)
export const bulkImportStudents = async (records) => {
  if (!Array.isArray(records) || records.length === 0) {
    throw new Error("No student records to import");
  }

  let added = 0;
  let skipped = 0;
  const errors = [];

  for (let i = 0; i < records.length; i += 1) {
    const rec = records[i];
    try {
      await addStudent(rec);
      added += 1;
    } catch (err) {
      skipped += 1;
      errors.push(`Row ${i + 1} (${rec.reg_no || "N/A"}): ${err.message}`);
    }
  }

  recordActivityLog(
    "CSV Bulk Import",
    `Imported ${added} student(s), skipped ${skipped}`,
    added > 0 ? "success" : "warning"
  );

  return {
    success: true,
    added,
    skipped,
    errors,
  };
};

// ==========================================
// PHASE 3: ACADEMIC MANAGEMENT API (COURSES, ENROLLMENTS, ATTENDANCE, GRADES)
// ==========================================
export const getCourses = async (includeArchived = false) => {
  const qs = includeArchived ? "?include_archived=true" : "";
  const response = await apiFetch(`/api/v1/courses${qs}`, { method: "GET" });
  if (!response.ok) return [];
  const data = await response.json().catch(() => ({}));
  return Array.isArray(data.courses) ? data.courses : [];
};

export const createCourseApi = async (coursePayload) => {
  const response = await apiFetch("/api/v1/courses", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(coursePayload),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(extractErrorMessage(data, "Failed to create course"));
  }
  recordActivityLog(
    "Course Created",
    `Created course ${coursePayload.course_code} (${coursePayload.course_name})`,
    "success"
  );
  return data;
};

export const archiveCourseApi = async (courseCode, archive = true) => {
  const response = await apiFetch(
    `/api/v1/courses/${encodeURIComponent(courseCode)}/archive`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ archive }),
    }
  );
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(extractErrorMessage(data, "Failed to update course status"));
  }
  return data;
};

export const getEnrollments = async (courseCode = "") => {
  const qs = courseCode
    ? `?course_code=${encodeURIComponent(courseCode)}`
    : "";
  const response = await apiFetch(`/api/v1/enrollments${qs}`, {
    method: "GET",
  });
  if (!response.ok) return [];
  const data = await response.json().catch(() => ({}));
  return Array.isArray(data.enrollments) ? data.enrollments : [];
};

export const enrollStudentApi = async (payload) => {
  const response = await apiFetch("/api/v1/enrollments", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(extractErrorMessage(data, "Failed to enroll student"));
  }
  recordActivityLog(
    "Student Enrolled",
    `Enrolled ${payload.reg_no} in ${payload.course_code}`,
    "success"
  );
  return data;
};

export const unenrollStudentApi = async (enrollmentId) => {
  const response = await apiFetch(
    `/api/v1/enrollments/${encodeURIComponent(enrollmentId)}`,
    { method: "DELETE" }
  );
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(extractErrorMessage(data, "Failed to remove enrollment"));
  }
  return data;
};

export const getAttendanceRecords = async (courseCode = "", date = "") => {
  const params = new URLSearchParams();
  if (courseCode) params.set("course_code", courseCode);
  if (date) params.set("date", date);
  const qs = params.toString() ? `?${params.toString()}` : "";
  const response = await apiFetch(`/api/v1/attendance${qs}`, { method: "GET" });
  if (!response.ok) return [];
  const data = await response.json().catch(() => ({}));
  return Array.isArray(data.attendance) ? data.attendance : [];
};

export const recordAttendanceApi = async (payload, isUpdate = false) => {
  const response = await apiFetch("/api/v1/attendance", {
    method: isUpdate ? "PUT" : "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(extractErrorMessage(data, "Failed to record attendance"));
  }
  return data;
};

export const submitBatchAttendanceApi = async (payload) => {
  const response = await apiFetch("/api/v1/attendance/batch", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(extractErrorMessage(data, "Batch attendance submission failed"));
  }
  recordActivityLog(
    "Classroom Attendance",
    `Submitted attendance for ${payload.course_code} on ${payload.date}`,
    "info"
  );
  return data;
};

export const getAttendanceReportApi = async (courseCode = "") => {
  const qs = courseCode
    ? `?course_code=${encodeURIComponent(courseCode)}`
    : "";
  const response = await apiFetch(`/api/v1/attendance/report${qs}`, {
    method: "GET",
  });
  if (!response.ok) {
    return { course_summaries: [], student_summaries: [] };
  }
  return response.json().catch(() => ({
    course_summaries: [],
    student_summaries: [],
  }));
};

export const getGradesApi = async (courseCode = "") => {
  const qs = courseCode
    ? `?course_code=${encodeURIComponent(courseCode)}`
    : "";
  const response = await apiFetch(`/api/v1/grades${qs}`, { method: "GET" });
  if (!response.ok) return [];
  const data = await response.json().catch(() => ({}));
  return Array.isArray(data.grades) ? data.grades : [];
};

export const recordGradeApi = async (payload, isUpdate = false) => {
  const response = await apiFetch("/api/v1/grades", {
    method: isUpdate ? "PUT" : "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(extractErrorMessage(data, "Failed to record grade"));
  }
  recordActivityLog(
    "Grade Recorded",
    `Recorded ${payload.assessment_type} marks for ${payload.reg_no} in ${payload.course_code}`,
    "success"
  );
  return data;
};

export const getGradesReportApi = async () => {
  const response = await apiFetch("/api/v1/grades/report", { method: "GET" });
  if (!response.ok) {
    return { course_reports: [], student_reports: [] };
  }
  return response.json().catch(() => ({
    course_reports: [],
    student_reports: [],
  }));
};

export const getGradingScaleApi = async () => {
  const response = await apiFetch("/api/v1/academics/grading-scale", {
    method: "GET",
  });
  if (!response.ok) return null;
  const data = await response.json().catch(() => ({}));
  return data.grading_scale || null;
};

export const updateGradingScaleApi = async (scalePayload) => {
  const response = await apiFetch("/api/v1/academics/grading-scale", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(scalePayload),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(extractErrorMessage(data, "Failed to update grading scale"));
  }
  return data;
};

// ==========================================
// PHASE 4: ADVANCED ANALYTICS, EXPORTS (PDF/EXCEL/CSV) & AI ASSISTANT
// ==========================================
const buildFilterQueryString = (filters = {}) => {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, val]) => {
    if (val !== undefined && val !== null && String(val).trim() !== "") {
      params.set(key, String(val).trim());
    }
  });
  const qs = params.toString();
  return qs ? `?${qs}` : "";
};

export const getAdvancedAnalyticsApi = async (filters = {}) => {
  const qs = buildFilterQueryString(filters);
  const response = await apiFetch(`/api/v1/analytics/advanced${qs}`, {
    method: "GET",
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(
      extractErrorMessage(data, "Failed to load advanced analytics")
    );
  }
  return data;
};

export const getReportPreviewApi = async (filters = {}) => {
  const qs = buildFilterQueryString(filters);
  const response = await apiFetch(`/api/v1/reports/preview${qs}`, {
    method: "GET",
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(extractErrorMessage(data, "Failed to load report preview"));
  }
  return data;
};

export const downloadReportExportApi = async (filters = {}) => {
  const response = await apiFetch("/api/v1/reports/export", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(filters),
  });

  if (!response.ok) {
    const errData = await response.json().catch(() => ({}));
    throw new Error(extractErrorMessage(errData, "Report export failed"));
  }

  const disposition = response.headers.get("Content-Disposition") || "";
  const match = disposition.match(/filename="?([^"]+)"?/i);
  const ext =
    filters.format === "pdf"
      ? "pdf"
      : filters.format === "xlsx" || filters.format === "excel"
      ? "xlsx"
      : "csv";
  const filename = match
    ? match[1]
    : `studentdb_${filters.report_type || "report"}.${ext}`;

  const blob = await response.blob();
  if (typeof window !== "undefined" && window.URL && window.URL.createObjectURL) {
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  }

  recordActivityLog(
    "Report Exported",
    `Exported ${filters.report_type || "report"} as ${ext.toUpperCase()} (${filename})`,
    "success"
  );

  return { success: true, filename };
};

export const getAiAssistantStatusApi = async () => {
  const response = await apiFetch("/api/v1/ai/status", { method: "GET" });
  if (!response.ok) return null;
  return response.json().catch(() => null);
};

export const queryAiAssistantApi = async (question, filters = {}) => {
  const response = await apiFetch("/api/v1/ai/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, filters }),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(
      extractErrorMessage(data, "AI Analytics Assistant request failed")
    );
  }
  return data;
};

