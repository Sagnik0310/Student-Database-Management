import React, { useState, useEffect, useCallback } from "react";
import {
  Box,
  Paper,
  Typography,
  Grid,
  TextField,
  Button,
  MenuItem,
  Table,
  TableHead,
  TableRow,
  TableCell,
  TableBody,
  Chip,
  Stack,
  Divider,
  LinearProgress,
  Switch,
  FormControlLabel,
} from "@mui/material";
import AddCircleOutlineRoundedIcon from "@mui/icons-material/AddCircleOutlineRounded";
import ArchiveOutlinedIcon from "@mui/icons-material/ArchiveOutlined";
import UnarchiveOutlinedIcon from "@mui/icons-material/UnarchiveOutlined";
import FactCheckRoundedIcon from "@mui/icons-material/FactCheckRounded";
import GradeRoundedIcon from "@mui/icons-material/GradeRounded";
import DeleteOutlineRoundedIcon from "@mui/icons-material/DeleteOutlineRounded";

import {
  getCourses,
  createCourseApi,
  archiveCourseApi,
  getEnrollments,
  enrollStudentApi,
  unenrollStudentApi,
  submitBatchAttendanceApi,
  getAttendanceReportApi,
  getGradesApi,
  recordGradeApi,
  getGradingScaleApi,
  updateGradingScaleApi,
} from "../services/api";

const ATTENDANCE_STATUSES = ["Present", "Absent", "Late", "Excused"];
const SESSIONS = ["Lecture", "Lab", "Tutorial", "Morning", "Afternoon"];
const ASSESSMENTS = ["Overall", "Midterm", "Final", "Internal", "Assignment", "Lab"];

// =========================================================
// 1. ACADEMICS WORKSPACE (COURSES & ENROLLMENTS)
// =========================================================
export function AcademicsWorkspace({
  students = [],
  currentUser,
  onNotify,
  onSelectBranchRoster,
}) {
  const isAdmin = currentUser?.role === "Admin";
  const canEnroll = isAdmin || currentUser?.role === "Faculty";

  const [courses, setCourses] = useState([]);
  const [enrollments, setEnrollments] = useState([]);
  const [showArchived, setShowArchived] = useState(false);
  const [courseSearch, setCourseSearch] = useState("");

  const [courseForm, setCourseForm] = useState({
    course_code: "",
    course_name: "",
    branch: "CSE",
    credits: 4,
    semester: "3",
    academic_year: "2025-2026",
    faculty_username: "faculty_cse",
    capacity: 60,
  });

  const [enrollForm, setEnrollForm] = useState({
    reg_no: "",
    course_code: "",
  });

  const loadAcademicsData = useCallback(async () => {
    const [crs, enr] = await Promise.all([
      getCourses(showArchived),
      getEnrollments(),
    ]);
    setCourses(crs);
    setEnrollments(enr);
  }, [showArchived]);

  useEffect(() => {
    loadAcademicsData();
  }, [loadAcademicsData]);

  const handleCreateCourse = async (e) => {
    e.preventDefault();
    try {
      await createCourseApi(courseForm);
      onNotify &&
        onNotify(`Created course ${courseForm.course_code}`, "success");
      setCourseForm((prev) => ({
        ...prev,
        course_code: "",
        course_name: "",
      }));
      loadAcademicsData();
    } catch (err) {
      onNotify && onNotify(err.message, "error");
    }
  };

  const handleToggleArchive = async (course) => {
    try {
      const archiveFlag = course.status !== "Archived";
      await archiveCourseApi(course.course_code, archiveFlag);
      onNotify &&
        onNotify(
          `${archiveFlag ? "Archived" : "Restored"} ${course.course_code}`,
          "info"
        );
      loadAcademicsData();
    } catch (err) {
      onNotify && onNotify(err.message, "error");
    }
  };

  const handleEnrollStudent = async (e) => {
    e.preventDefault();
    try {
      const res = await enrollStudentApi(enrollForm);
      onNotify && onNotify(res.message || "Student enrolled", "success");
      setEnrollForm({ reg_no: "", course_code: "" });
      loadAcademicsData();
    } catch (err) {
      onNotify && onNotify(err.message, "error");
    }
  };

  const handleUnenroll = async (enrollmentId) => {
    try {
      await unenrollStudentApi(enrollmentId);
      onNotify && onNotify("Enrollment removed", "info");
      loadAcademicsData();
    } catch (err) {
      onNotify && onNotify(err.message, "error");
    }
  };

  const filteredCourses = courses.filter((c) => {
    const q = courseSearch.trim().toLowerCase();
    if (!q) return true;
    return (
      c.course_code.toLowerCase().includes(q) ||
      c.course_name.toLowerCase().includes(q) ||
      c.branch.toLowerCase().includes(q)
    );
  });

  // Department cards derived from student records
  const branchCounts = {};
  students.forEach((s) => {
    const b = s.branch || "Unassigned";
    branchCounts[b] = (branchCounts[b] || 0) + 1;
  });

  return (
    <Box>
      {/* Department Summary Row */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        {Object.entries(branchCounts).map(([branch, count]) => (
          <Grid size={{ xs: 12, sm: 6, md: 3 }} key={branch}>
            <Paper
              elevation={0}
              sx={{
                p: 2,
                borderRadius: 3,
                border: "1px solid",
                borderColor: "divider",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <Box>
                <Chip
                  label={branch}
                  size="small"
                  color="primary"
                  sx={{ fontWeight: 700, mb: 0.5 }}
                />
                <Typography variant="h6" sx={{ fontWeight: 800 }}>
                  {count} Student(s)
                </Typography>
              </Box>
              {onSelectBranchRoster && (
                <Button
                  size="small"
                  variant="outlined"
                  onClick={() => onSelectBranchRoster(branch)}
                  sx={{ textTransform: "none" }}
                >
                  Roster
                </Button>
              )}
            </Paper>
          </Grid>
        ))}
      </Grid>

      <Grid container spacing={3}>
        {/* Create Course Form (Admin) & Enroll Student Form */}
        {canEnroll && (
          <Grid size={{ xs: 12, lg: 4 }}>
            <Stack spacing={3}>
              {isAdmin && (
                <Paper
                  elevation={0}
                  sx={{
                    p: 2.5,
                    borderRadius: 3,
                    border: "1px solid",
                    borderColor: "divider",
                  }}
                >
                  <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 2 }}>
                    Create Academic Course
                  </Typography>
                  <form onSubmit={handleCreateCourse}>
                    <Stack spacing={1.5}>
                      <TextField
                        size="small"
                        label="Course Code (e.g. CS301) *"
                        value={courseForm.course_code}
                        onChange={(e) =>
                          setCourseForm((p) => ({
                            ...p,
                            course_code: e.target.value,
                          }))
                        }
                        required
                      />
                      <TextField
                        size="small"
                        label="Course Name *"
                        value={courseForm.course_name}
                        onChange={(e) =>
                          setCourseForm((p) => ({
                            ...p,
                            course_name: e.target.value,
                          }))
                        }
                        required
                      />
                      <Stack direction="row" spacing={1.5}>
                        <TextField
                          size="small"
                          label="Branch *"
                          value={courseForm.branch}
                          onChange={(e) =>
                            setCourseForm((p) => ({
                              ...p,
                              branch: e.target.value,
                            }))
                          }
                          fullWidth
                        />
                        <TextField
                          size="small"
                          type="number"
                          label="Credits *"
                          value={courseForm.credits}
                          onChange={(e) =>
                            setCourseForm((p) => ({
                              ...p,
                              credits: e.target.value,
                            }))
                          }
                          fullWidth
                        />
                      </Stack>
                      <Stack direction="row" spacing={1.5}>
                        <TextField
                          size="small"
                          label="Semester"
                          value={courseForm.semester}
                          onChange={(e) =>
                            setCourseForm((p) => ({
                              ...p,
                              semester: e.target.value,
                            }))
                          }
                          fullWidth
                        />
                        <TextField
                          size="small"
                          type="number"
                          label="Capacity"
                          value={courseForm.capacity}
                          onChange={(e) =>
                            setCourseForm((p) => ({
                              ...p,
                              capacity: e.target.value,
                            }))
                          }
                          fullWidth
                        />
                      </Stack>
                      <TextField
                        size="small"
                        label="Assigned Faculty Username"
                        value={courseForm.faculty_username}
                        onChange={(e) =>
                          setCourseForm((p) => ({
                            ...p,
                            faculty_username: e.target.value,
                          }))
                        }
                      />
                      <Button
                        type="submit"
                        variant="contained"
                        startIcon={<AddCircleOutlineRoundedIcon />}
                        sx={{ textTransform: "none", fontWeight: 600 }}
                      >
                        Add Course
                      </Button>
                    </Stack>
                  </form>
                </Paper>
              )}

              <Paper
                elevation={0}
                sx={{
                  p: 2.5,
                  borderRadius: 3,
                  border: "1px solid",
                  borderColor: "divider",
                }}
              >
                <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 2 }}>
                  Enroll Student in Course
                </Typography>
                <form onSubmit={handleEnrollStudent}>
                  <Stack spacing={1.5}>
                    <TextField
                      select
                      size="small"
                      label="Select Student *"
                      value={enrollForm.reg_no}
                      onChange={(e) =>
                        setEnrollForm((p) => ({
                          ...p,
                          reg_no: e.target.value,
                        }))
                      }
                      required
                    >
                      {students.map((s) => (
                        <MenuItem key={s.reg_no} value={s.reg_no}>
                          {s.name} ({s.reg_no} • {s.branch})
                        </MenuItem>
                      ))}
                    </TextField>

                    <TextField
                      select
                      size="small"
                      label="Select Active Course *"
                      value={enrollForm.course_code}
                      onChange={(e) =>
                        setEnrollForm((p) => ({
                          ...p,
                          course_code: e.target.value,
                        }))
                      }
                      required
                    >
                      {courses
                        .filter((c) => c.status === "Active")
                        .map((c) => (
                          <MenuItem key={c.course_code} value={c.course_code}>
                            {c.course_code} — {c.course_name} ({c.credits} Cr)
                          </MenuItem>
                        ))}
                    </TextField>

                    <Button
                      type="submit"
                      variant="contained"
                      color="secondary"
                      sx={{ textTransform: "none", fontWeight: 600 }}
                    >
                      Enroll Student
                    </Button>
                  </Stack>
                </form>
              </Paper>
            </Stack>
          </Grid>
        )}

        {/* Courses Catalog & Active Enrollments Tables */}
        <Grid size={{ xs: 12, lg: canEnroll ? 8 : 12 }}>
          <Stack spacing={3}>
            <Paper
              elevation={0}
              sx={{
                p: 2.5,
                borderRadius: 3,
                border: "1px solid",
                borderColor: "divider",
              }}
            >
              <Box
                sx={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  flexWrap: "wrap",
                  gap: 1.5,
                  mb: 2,
                }}
              >
                <Typography variant="h6" sx={{ fontWeight: 700 }}>
                  Course Catalog ({filteredCourses.length})
                </Typography>
                <Stack direction="row" spacing={1.5} alignItems="center">
                  <TextField
                    size="small"
                    placeholder="Filter courses..."
                    value={courseSearch}
                    onChange={(e) => setCourseSearch(e.target.value)}
                  />
                  {isAdmin && (
                    <FormControlLabel
                      control={
                        <Switch
                          size="small"
                          checked={showArchived}
                          onChange={(e) => setShowArchived(e.target.checked)}
                        />
                      }
                      label="Show Archived"
                    />
                  )}
                </Stack>
              </Box>

              {filteredCourses.length === 0 ? (
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{ py: 3, textAlign: "center" }}
                >
                  No courses created yet. Use the form to add a course.
                </Typography>
              ) : (
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell sx={{ fontWeight: 700 }}>Code</TableCell>
                      <TableCell sx={{ fontWeight: 700 }}>Course Name</TableCell>
                      <TableCell sx={{ fontWeight: 700 }}>Branch</TableCell>
                      <TableCell sx={{ fontWeight: 700 }}>Credits</TableCell>
                      <TableCell sx={{ fontWeight: 700 }}>Enrolled</TableCell>
                      <TableCell sx={{ fontWeight: 700 }}>Status</TableCell>
                      {isAdmin && (
                        <TableCell align="right" sx={{ fontWeight: 700 }}>
                          Action
                        </TableCell>
                      )}
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {filteredCourses.map((c) => (
                      <TableRow key={c.course_code} hover>
                        <TableCell
                          sx={{ fontFamily: "monospace", fontWeight: 700 }}
                        >
                          {c.course_code}
                        </TableCell>
                        <TableCell sx={{ fontWeight: 600 }}>
                          {c.course_name}
                        </TableCell>
                        <TableCell>
                          <Chip label={c.branch} size="small" variant="outlined" />
                        </TableCell>
                        <TableCell>{c.credits}</TableCell>
                        <TableCell>
                          {c.enrolled_count || 0} / {c.capacity}
                        </TableCell>
                        <TableCell>
                          <Chip
                            size="small"
                            label={c.status}
                            color={c.status === "Active" ? "success" : "default"}
                          />
                        </TableCell>
                        {isAdmin && (
                          <TableCell align="right">
                            <Button
                              size="small"
                              color={
                                c.status === "Active" ? "warning" : "primary"
                              }
                              startIcon={
                                c.status === "Active" ? (
                                  <ArchiveOutlinedIcon fontSize="small" />
                                ) : (
                                  <UnarchiveOutlinedIcon fontSize="small" />
                                )
                              }
                              onClick={() => handleToggleArchive(c)}
                              sx={{ textTransform: "none" }}
                            >
                              {c.status === "Active" ? "Archive" : "Restore"}
                            </Button>
                          </TableCell>
                        )}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </Paper>

            <Paper
              elevation={0}
              sx={{
                p: 2.5,
                borderRadius: 3,
                border: "1px solid",
                borderColor: "divider",
              }}
            >
              <Typography variant="h6" sx={{ fontWeight: 700, mb: 2 }}>
                Course Enrollments ({enrollments.length})
              </Typography>
              {enrollments.length === 0 ? (
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{ py: 3, textAlign: "center" }}
                >
                  No course enrollments recorded yet.
                </Typography>
              ) : (
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell sx={{ fontWeight: 700 }}>Reg No</TableCell>
                      <TableCell sx={{ fontWeight: 700 }}>Student</TableCell>
                      <TableCell sx={{ fontWeight: 700 }}>Course</TableCell>
                      <TableCell sx={{ fontWeight: 700 }}>Semester</TableCell>
                      <TableCell sx={{ fontWeight: 700 }}>Credits</TableCell>
                      {isAdmin && (
                        <TableCell align="right" sx={{ fontWeight: 700 }}>
                          Remove
                        </TableCell>
                      )}
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {enrollments.map((enr) => (
                      <TableRow key={enr.enrollment_id} hover>
                        <TableCell
                          sx={{ fontFamily: "monospace", fontWeight: 600 }}
                        >
                          {enr.reg_no}
                        </TableCell>
                        <TableCell sx={{ fontWeight: 600 }}>
                          {enr.student_name}
                        </TableCell>
                        <TableCell>
                          {enr.course_code} — {enr.course_name}
                        </TableCell>
                        <TableCell>Sem {enr.semester}</TableCell>
                        <TableCell>{enr.credits}</TableCell>
                        {isAdmin && (
                          <TableCell align="right">
                            <Button
                              size="small"
                              color="error"
                              startIcon={<DeleteOutlineRoundedIcon />}
                              onClick={() => handleUnenroll(enr.enrollment_id)}
                              sx={{ textTransform: "none" }}
                            >
                              Unenroll
                            </Button>
                          </TableCell>
                        )}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </Paper>
          </Stack>
        </Grid>
      </Grid>
    </Box>
  );
}

// =========================================================
// 2. ATTENDANCE WORKSPACE (CLASSROOM ROLL CALL & REPORTS)
// =========================================================
export function AttendanceWorkspace({
  students = [],
  currentUser,
  onNotify,
  onRefreshStudents,
}) {
  const canRecord =
    currentUser?.role === "Admin" || currentUser?.role === "Faculty";

  const [courses, setCourses] = useState([]);
  const [enrollments, setEnrollments] = useState([]);
  const [selectedCourse, setSelectedCourse] = useState("");
  const [selectedDate, setSelectedDate] = useState(() =>
    new Date().toISOString().slice(0, 10)
  );
  const [selectedSession, setSelectedSession] = useState("Lecture");
  const [statusMap, setStatusMap] = useState({});
  const [report, setReport] = useState({
    formula: "",
    course_summaries: [],
    student_summaries: [],
  });

  const loadAttendanceData = useCallback(async () => {
    const [crs, enr, rep] = await Promise.all([
      getCourses(false),
      getEnrollments(selectedCourse),
      getAttendanceReportApi(selectedCourse),
    ]);
    setCourses(crs);
    setEnrollments(enr);
    setReport(rep);
    if (!selectedCourse && crs.length > 0) {
      setSelectedCourse(crs[0].course_code);
    }
  }, [selectedCourse]);

  useEffect(() => {
    loadAttendanceData();
  }, [loadAttendanceData]);

  const handleBatchSubmit = async () => {
    if (!selectedCourse) {
      onNotify && onNotify("Select a course first", "warning");
      return;
    }
    const enrolledList = enrollments.filter(
      (e) => e.course_code === selectedCourse
    );
    if (enrolledList.length === 0) {
      onNotify &&
        onNotify("No students enrolled in this course yet", "warning");
      return;
    }
    const records = enrolledList.map((e) => ({
      reg_no: e.reg_no,
      status: statusMap[e.reg_no] || "Present",
    }));

    try {
      const res = await submitBatchAttendanceApi({
        course_code: selectedCourse,
        date: selectedDate,
        session: selectedSession,
        records,
        allow_update: true,
      });
      onNotify && onNotify(res.message || "Attendance saved", "success");
      loadAttendanceData();
      onRefreshStudents && onRefreshStudents(true);
    } catch (err) {
      onNotify && onNotify(err.message, "error");
    }
  };

  return (
    <Box>
      {/* Formula & Compliance Header */}
      <Paper
        elevation={0}
        sx={{
          p: 2.5,
          mb: 3,
          borderRadius: 3,
          border: "1px solid",
          borderColor: "divider",
        }}
      >
        <Typography variant="h6" sx={{ fontWeight: 700 }}>
          Course Attendance Management & Reports
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {report.formula ||
            "Attendance % = ((Present + 0.5 * Late) / (Present + Absent + Late)) * 100 (Excused sessions excluded from penalty)"}
        </Typography>
      </Paper>

      {/* Classroom Roll-Call Interface (Admin / Faculty) */}
      {canRecord && (
        <Paper
          elevation={0}
          sx={{
            p: 2.5,
            mb: 3,
            borderRadius: 3,
            border: "1px solid",
            borderColor: "divider",
          }}
        >
          <Box
            sx={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              flexWrap: "wrap",
              gap: 2,
              mb: 2,
            }}
          >
            <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
              Classroom Roll Call Sheet
            </Typography>
            <Stack direction="row" spacing={1.5} flexWrap="wrap" useFlexGap>
              <TextField
                select
                size="small"
                label="Course"
                value={selectedCourse}
                onChange={(e) => setSelectedCourse(e.target.value)}
                sx={{ minWidth: 200 }}
              >
                {courses.map((c) => (
                  <MenuItem key={c.course_code} value={c.course_code}>
                    {c.course_code} — {c.course_name}
                  </MenuItem>
                ))}
              </TextField>

              <TextField
                size="small"
                type="date"
                label="Session Date"
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
                slotProps={{ inputLabel: { shrink: true } }}
              />

              <TextField
                select
                size="small"
                label="Session"
                value={selectedSession}
                onChange={(e) => setSelectedSession(e.target.value)}
                sx={{ minWidth: 130 }}
              >
                {SESSIONS.map((s) => (
                  <MenuItem key={s} value={s}>
                    {s}
                  </MenuItem>
                ))}
              </TextField>

              <Button
                variant="contained"
                startIcon={<FactCheckRoundedIcon />}
                onClick={handleBatchSubmit}
                sx={{ textTransform: "none", fontWeight: 600 }}
              >
                Save Classroom Attendance
              </Button>
            </Stack>
          </Box>

          {enrollments.length === 0 ? (
            <Typography variant="body2" color="text.secondary">
              Enroll students into courses in the <strong>Academics</strong> tab
              to take classroom roll-call attendance.
            </Typography>
          ) : (
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell sx={{ fontWeight: 700 }}>Reg No</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>Student Name</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>Course</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>Mark Status</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {enrollments.map((enr) => {
                  const currentStatus = statusMap[enr.reg_no] || "Present";
                  return (
                    <TableRow key={enr.enrollment_id} hover>
                      <TableCell
                        sx={{ fontFamily: "monospace", fontWeight: 600 }}
                      >
                        {enr.reg_no}
                      </TableCell>
                      <TableCell sx={{ fontWeight: 600 }}>
                        {enr.student_name}
                      </TableCell>
                      <TableCell>{enr.course_code}</TableCell>
                      <TableCell>
                        <Stack direction="row" spacing={1}>
                          {ATTENDANCE_STATUSES.map((st) => (
                            <Chip
                              key={st}
                              label={st}
                              size="small"
                              clickable
                              color={
                                currentStatus === st
                                  ? st === "Present"
                                    ? "success"
                                    : st === "Absent"
                                    ? "error"
                                    : st === "Late"
                                    ? "warning"
                                    : "info"
                                  : "default"
                              }
                              variant={
                                currentStatus === st ? "filled" : "outlined"
                              }
                              onClick={() =>
                                setStatusMap((prev) => ({
                                  ...prev,
                                  [enr.reg_no]: st,
                                }))
                              }
                            />
                          ))}
                        </Stack>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </Paper>
      )}

      {/* Course-wise Attendance Report */}
      {report.course_summaries?.length > 0 && (
        <Paper
          elevation={0}
          sx={{
            p: 2.5,
            mb: 3,
            borderRadius: 3,
            border: "1px solid",
            borderColor: "divider",
          }}
        >
          <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 2 }}>
            Course-Wise Attendance Report
          </Typography>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell sx={{ fontWeight: 700 }}>Course Code</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Course Name</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>
                  Sessions (P / L / A / E)
                </TableCell>
                <TableCell sx={{ fontWeight: 700 }}>
                  Course Attendance (%)
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {report.course_summaries.map((cs) => (
                <TableRow key={cs.course_code} hover>
                  <TableCell sx={{ fontFamily: "monospace", fontWeight: 700 }}>
                    {cs.course_code}
                  </TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>
                    {cs.course_name}
                  </TableCell>
                  <TableCell>
                    {cs.present ?? 0} / {cs.late ?? 0} / {cs.absent ?? 0} /{" "}
                    {cs.excused ?? 0}
                  </TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>
                    {cs.attendance_percentage ?? cs.attendance_pct ?? 0}%
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Paper>
      )}

      {/* Student-wise Attendance Report */}
      <Paper
        elevation={0}
        sx={{
          p: 2.5,
          borderRadius: 3,
          border: "1px solid",
          borderColor: "divider",
        }}
      >
        <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 2 }}>
          Student Attendance Summary Report
        </Typography>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell sx={{ fontWeight: 700 }}>Reg No</TableCell>
              <TableCell sx={{ fontWeight: 700 }}>Student Name</TableCell>
              <TableCell sx={{ fontWeight: 700 }}>Branch</TableCell>
              <TableCell sx={{ fontWeight: 700 }}>
                Sessions (P / L / A / E)
              </TableCell>
              <TableCell sx={{ fontWeight: 700 }}>Attendance (%)</TableCell>
              <TableCell sx={{ fontWeight: 700 }}>Standing</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {(report.student_summaries?.length > 0
              ? report.student_summaries
              : students.map((s) => ({
                  reg_no: s.reg_no,
                  student_name: s.name,
                  branch: s.branch,
                  present: "-",
                  late: "-",
                  absent: "-",
                  excused: "-",
                  attendance_percentage: s.attendance_pct,
                  below_threshold:
                    s.attendance_pct !== null &&
                    s.attendance_pct !== undefined &&
                    Number(s.attendance_pct) < 75,
                }))
            ).map((row) => {
              const pct =
                row.attendance_percentage !== null &&
                row.attendance_percentage !== undefined
                  ? Number(row.attendance_percentage)
                  : null;
              return (
                <TableRow key={row.reg_no} hover>
                  <TableCell sx={{ fontFamily: "monospace", fontWeight: 600 }}>
                    {row.reg_no}
                  </TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>
                    {row.student_name}
                  </TableCell>
                  <TableCell>{row.branch}</TableCell>
                  <TableCell>
                    {row.present} / {row.late} / {row.absent} / {row.excused}
                  </TableCell>
                  <TableCell sx={{ minWidth: 150 }}>
                    {pct !== null ? (
                      <Box>
                        <Typography variant="caption" sx={{ fontWeight: 700 }}>
                          {pct.toFixed(1)}%
                        </Typography>
                        <LinearProgress
                          variant="determinate"
                          color={row.below_threshold ? "warning" : "success"}
                          value={Math.min(100, pct)}
                          sx={{ height: 6, borderRadius: 2, mt: 0.5 }}
                        />
                      </Box>
                    ) : (
                      <Typography variant="caption" color="text.secondary">
                        No sessions logged
                      </Typography>
                    )}
                  </TableCell>
                  <TableCell>
                    <Chip
                      size="small"
                      label={
                        pct === null
                          ? "Pending"
                          : row.below_threshold
                          ? "Shortage (<75%)"
                          : "Good Standing"
                      }
                      color={
                        pct === null
                          ? "default"
                          : row.below_threshold
                          ? "warning"
                          : "success"
                      }
                    />
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </Paper>
    </Box>
  );
}

// =========================================================
// 3. PERFORMANCE WORKSPACE (GRADES, GPA/CGPA & GRADING SCALE)
// =========================================================
export function PerformanceWorkspace({
  students = [],
  currentUser,
  onNotify,
  onRefreshStudents,
}) {
  const isAdmin = currentUser?.role === "Admin";
  const canGrade = isAdmin || currentUser?.role === "Faculty";

  const [courses, setCourses] = useState([]);
  const [grades, setGrades] = useState([]);
  const [scale, setScale] = useState(null);

  const [gradeForm, setGradeForm] = useState({
    reg_no: "",
    course_code: "",
    assessment_type: "Overall",
    marks_obtained: "",
    max_marks: 100,
  });

  const loadGradesData = useCallback(async () => {
    const [crs, grd, scl] = await Promise.all([
      getCourses(false),
      getGradesApi(),
      getGradingScaleApi(),
    ]);
    setCourses(crs);
    setGrades(grd);
    setScale(scl);
  }, []);

  useEffect(() => {
    loadGradesData();
  }, [loadGradesData]);

  const handleRecordGrade = async (e) => {
    e.preventDefault();
    try {
      const res = await recordGradeApi(
        {
          ...gradeForm,
          marks_obtained: Number(gradeForm.marks_obtained),
          max_marks: Number(gradeForm.max_marks),
        },
        true
      );
      onNotify && onNotify(res.message || "Grade recorded", "success");
      setGradeForm((p) => ({ ...p, marks_obtained: "" }));
      loadGradesData();
      onRefreshStudents && onRefreshStudents(true);
    } catch (err) {
      onNotify && onNotify(err.message, "error");
    }
  };

  const handleApplyScalePreset = async (presetType) => {
    const payload =
      presetType === "4.0"
        ? {
            scale_name: "US 4.0 GPA Scale",
            max_grade_points: 4.0,
            late_attendance_weight: 0.5,
            min_attendance_threshold: 75.0,
            bands: [
              { min_percentage: 90, letter_grade: "A", grade_points: 4.0 },
              { min_percentage: 80, letter_grade: "B", grade_points: 3.0 },
              { min_percentage: 70, letter_grade: "C", grade_points: 2.0 },
              { min_percentage: 60, letter_grade: "D", grade_points: 1.0 },
              { min_percentage: 0, letter_grade: "F", grade_points: 0.0 },
            ],
          }
        : {
            scale_name: "Standard 10-Point CBCS Scale",
            max_grade_points: 10.0,
            late_attendance_weight: 0.5,
            min_attendance_threshold: 75.0,
            bands: [
              { min_percentage: 90, letter_grade: "O", grade_points: 10.0 },
              { min_percentage: 80, letter_grade: "A+", grade_points: 9.0 },
              { min_percentage: 70, letter_grade: "A", grade_points: 8.0 },
              { min_percentage: 60, letter_grade: "B+", grade_points: 7.0 },
              { min_percentage: 50, letter_grade: "B", grade_points: 6.0 },
              { min_percentage: 40, letter_grade: "C", grade_points: 5.0 },
              { min_percentage: 0, letter_grade: "F", grade_points: 0.0 },
            ],
          };

    try {
      await updateGradingScaleApi(payload);
      onNotify &&
        onNotify(`Activated ${payload.scale_name}`, "success");
      loadGradesData();
    } catch (err) {
      onNotify && onNotify(err.message, "error");
    }
  };

  return (
    <Box>
      <Grid container spacing={3}>
        {canGrade && (
          <Grid size={{ xs: 12, lg: 4 }}>
            <Stack spacing={3}>
              <Paper
                elevation={0}
                sx={{
                  p: 2.5,
                  borderRadius: 3,
                  border: "1px solid",
                  borderColor: "divider",
                }}
              >
                <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 2 }}>
                  Record Assessment Marks
                </Typography>
                <form onSubmit={handleRecordGrade}>
                  <Stack spacing={1.5}>
                    <TextField
                      select
                      size="small"
                      label="Student *"
                      value={gradeForm.reg_no}
                      onChange={(e) =>
                        setGradeForm((p) => ({ ...p, reg_no: e.target.value }))
                      }
                      required
                    >
                      {students.map((s) => (
                        <MenuItem key={s.reg_no} value={s.reg_no}>
                          {s.name} ({s.reg_no})
                        </MenuItem>
                      ))}
                    </TextField>

                    <TextField
                      select
                      size="small"
                      label="Course *"
                      value={gradeForm.course_code}
                      onChange={(e) =>
                        setGradeForm((p) => ({
                          ...p,
                          course_code: e.target.value,
                        }))
                      }
                      required
                    >
                      {courses.map((c) => (
                        <MenuItem key={c.course_code} value={c.course_code}>
                          {c.course_code} — {c.course_name} ({c.credits} Cr)
                        </MenuItem>
                      ))}
                    </TextField>

                    <TextField
                      select
                      size="small"
                      label="Assessment Type"
                      value={gradeForm.assessment_type}
                      onChange={(e) =>
                        setGradeForm((p) => ({
                          ...p,
                          assessment_type: e.target.value,
                        }))
                      }
                    >
                      {ASSESSMENTS.map((a) => (
                        <MenuItem key={a} value={a}>
                          {a}
                        </MenuItem>
                      ))}
                    </TextField>

                    <Stack direction="row" spacing={1.5}>
                      <TextField
                        size="small"
                        type="number"
                        label="Marks Obtained *"
                        value={gradeForm.marks_obtained}
                        onChange={(e) =>
                          setGradeForm((p) => ({
                            ...p,
                            marks_obtained: e.target.value,
                          }))
                        }
                        required
                        fullWidth
                      />
                      <TextField
                        size="small"
                        type="number"
                        label="Max Marks *"
                        value={gradeForm.max_marks}
                        onChange={(e) =>
                          setGradeForm((p) => ({
                            ...p,
                            max_marks: e.target.value,
                          }))
                        }
                        required
                        fullWidth
                      />
                    </Stack>

                    <Button
                      type="submit"
                      variant="contained"
                      startIcon={<GradeRoundedIcon />}
                      sx={{ textTransform: "none", fontWeight: 600 }}
                    >
                      Save Assessment Grade
                    </Button>
                  </Stack>
                </form>
              </Paper>

              {/* Configurable Grading Scale Viewer / Switcher */}
              <Paper
                elevation={0}
                sx={{
                  p: 2.5,
                  borderRadius: 3,
                  border: "1px solid",
                  borderColor: "divider",
                }}
              >
                <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 0.5 }}>
                  Active Grading Scale Rules
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {scale?.scale_name || "Standard 10-Point CBCS Scale"} •
                  Formula: Credit-Weighted CGPA
                </Typography>

                <Divider sx={{ my: 1.5 }} />

                <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mb: 2 }}>
                  {(scale?.bands || []).map((b) => (
                    <Chip
                      key={b.letter_grade}
                      size="small"
                      variant="outlined"
                      label={`${b.letter_grade} (>=${b.min_percentage}%): ${b.grade_points} GP`}
                    />
                  ))}
                </Stack>

                {isAdmin && (
                  <Stack direction="row" spacing={1}>
                    <Button
                      size="small"
                      variant="outlined"
                      onClick={() => handleApplyScalePreset("10.0")}
                      sx={{ textTransform: "none" }}
                    >
                      Use 10.0 CBCS Scale
                    </Button>
                    <Button
                      size="small"
                      variant="outlined"
                      onClick={() => handleApplyScalePreset("4.0")}
                      sx={{ textTransform: "none" }}
                    >
                      Use 4.0 GPA Scale
                    </Button>
                  </Stack>
                )}
              </Paper>
            </Stack>
          </Grid>
        )}

        <Grid size={{ xs: 12, lg: canGrade ? 8 : 12 }}>
          <Stack spacing={3}>
            <Paper
              elevation={0}
              sx={{
                p: 2.5,
                borderRadius: 3,
                border: "1px solid",
                borderColor: "divider",
              }}
            >
              <Typography variant="h6" sx={{ fontWeight: 700, mb: 2 }}>
                Recorded Course Assessments ({grades.length})
              </Typography>
              {grades.length === 0 ? (
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{ py: 3, textAlign: "center" }}
                >
                  No course assessments recorded yet. Enroll students and enter
                  marks to compute credit-weighted GPA.
                </Typography>
              ) : (
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell sx={{ fontWeight: 700 }}>Reg No</TableCell>
                      <TableCell sx={{ fontWeight: 700 }}>Student</TableCell>
                      <TableCell sx={{ fontWeight: 700 }}>Course</TableCell>
                      <TableCell sx={{ fontWeight: 700 }}>Assessment</TableCell>
                      <TableCell sx={{ fontWeight: 700 }}>Marks</TableCell>
                      <TableCell sx={{ fontWeight: 700 }}>Grade</TableCell>
                      <TableCell sx={{ fontWeight: 700 }}>Points</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {grades.map((g) => (
                      <TableRow key={g.grade_id} hover>
                        <TableCell
                          sx={{ fontFamily: "monospace", fontWeight: 600 }}
                        >
                          {g.reg_no}
                        </TableCell>
                        <TableCell sx={{ fontWeight: 600 }}>
                          {g.student_name}
                        </TableCell>
                        <TableCell>{g.course_code}</TableCell>
                        <TableCell>{g.assessment_type}</TableCell>
                        <TableCell>
                          {g.marks_obtained} / {g.max_marks} ({g.percentage}%)
                        </TableCell>
                        <TableCell>
                          <Chip
                            size="small"
                            label={g.letter_grade}
                            color={
                              g.letter_grade === "F" ? "error" : "primary"
                            }
                            sx={{ fontWeight: 700 }}
                          />
                        </TableCell>
                        <TableCell sx={{ fontWeight: 700 }}>
                          {g.grade_points}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </Paper>

            {/* Student CGPA Standing Table */}
            <Paper
              elevation={0}
              sx={{
                p: 2.5,
                borderRadius: 3,
                border: "1px solid",
                borderColor: "divider",
              }}
            >
              <Typography variant="h6" sx={{ fontWeight: 700, mb: 2 }}>
                Student Cumulative GPA (CGPA) Standing
              </Typography>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 700 }}>Reg No</TableCell>
                    <TableCell sx={{ fontWeight: 700 }}>Student Name</TableCell>
                    <TableCell sx={{ fontWeight: 700 }}>Branch</TableCell>
                    <TableCell sx={{ fontWeight: 700 }}>CGPA</TableCell>
                    <TableCell sx={{ fontWeight: 700 }}>Standing</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {students.map((s) => {
                    const gpa =
                      s.gpa !== null && s.gpa !== undefined
                        ? Number(s.gpa)
                        : null;
                    return (
                      <TableRow key={s.reg_no} hover>
                        <TableCell
                          sx={{ fontFamily: "monospace", fontWeight: 600 }}
                        >
                          {s.reg_no}
                        </TableCell>
                        <TableCell sx={{ fontWeight: 600 }}>{s.name}</TableCell>
                        <TableCell>{s.branch}</TableCell>
                        <TableCell sx={{ fontWeight: 700 }}>
                          {gpa !== null ? gpa.toFixed(2) : "Not Graded"}
                        </TableCell>
                        <TableCell>
                          <Chip
                            size="small"
                            label={
                              gpa === null
                                ? "Unassessed"
                                : gpa >= 8.5
                                ? "Distinction"
                                : gpa >= 7.0
                                ? "First Class"
                                : gpa >= 5.0
                                ? "Pass"
                                : "Academic Support"
                            }
                            color={
                              gpa === null
                                ? "default"
                                : gpa >= 7.0
                                ? "success"
                                : "info"
                            }
                          />
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </Paper>
          </Stack>
        </Grid>
      </Grid>
    </Box>
  );
}
