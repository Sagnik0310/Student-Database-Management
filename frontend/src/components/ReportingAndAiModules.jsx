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
  Alert,
  CircularProgress,
} from "@mui/material";
import PictureAsPdfRoundedIcon from "@mui/icons-material/PictureAsPdfRounded";
import TableViewRoundedIcon from "@mui/icons-material/TableViewRounded";
import FileDownloadRoundedIcon from "@mui/icons-material/FileDownloadRounded";
import AutoAwesomeRoundedIcon from "@mui/icons-material/AutoAwesomeRounded";
import SendRoundedIcon from "@mui/icons-material/SendRounded";
import DeleteSweepRoundedIcon from "@mui/icons-material/DeleteSweepRounded";
import FilterAltRoundedIcon from "@mui/icons-material/FilterAltRounded";
import RestartAltRoundedIcon from "@mui/icons-material/RestartAltRounded";
import VerifiedUserRoundedIcon from "@mui/icons-material/VerifiedUserRounded";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
} from "recharts";

import {
  getAdvancedAnalyticsApi,
  getReportPreviewApi,
  downloadReportExportApi,
  getAiAssistantStatusApi,
  queryAiAssistantApi,
  getCourses,
} from "../services/api";

const REPORT_TYPES = [
  {
    value: "student_directory",
    label: "Student Directory & Academic Standing",
    roles: ["Admin", "Faculty", "Student"],
  },
  {
    value: "course_enrollment",
    label: "Course Enrollment & Capacity Report",
    roles: ["Admin", "Faculty", "Student"],
  },
  {
    value: "attendance_register",
    label: "Attendance Register & Compliance Report",
    roles: ["Admin", "Faculty", "Student"],
  },
  {
    value: "grade_sheet",
    label: "Course Assessment & Grade Sheet",
    roles: ["Admin", "Faculty", "Student"],
  },
  {
    value: "academic_transcript",
    label: "Student Academic Transcript (Credit-Weighted CGPA)",
    roles: ["Admin", "Faculty", "Student"],
  },
  {
    value: "executive_summary",
    label: "Institutional Executive Summary (Branch, Semester & Course)",
    roles: ["Admin", "Faculty"],
  },
];

// =========================================================
// 1. OPTIONAL AI ANALYTICS ASSISTANT PANEL
// =========================================================
export function AiAnalyticsAssistantPanel({
  activeFilters = {},
  currentUser,
  onNotify,
}) {
  const [aiStatus, setAiStatus] = useState(null);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [messages, setMessages] = useState([]);

  useEffect(() => {
    let mounted = true;
    getAiAssistantStatusApi().then((st) => {
      if (mounted && st) setAiStatus(st);
    });
    return () => {
      mounted = false;
    };
  }, []);

  const handleAskQuestion = async (promptText) => {
    const q = String(promptText ?? question).trim();
    if (!q) {
      setErrorMsg("Please enter a question for the AI Analytics Assistant.");
      return;
    }

    setErrorMsg("");
    setLoading(true);
    const userEntry = {
      id: `u-${Date.now()}`,
      sender: "user",
      text: q,
      timestamp: new Date().toLocaleTimeString(),
    };
    setMessages((prev) => [...prev, userEntry]);
    if (!promptText) setQuestion("");

    try {
      const res = await queryAiAssistantApi(q, activeFilters);
      const botEntry = {
        id: `a-${Date.now()}`,
        sender: "assistant",
        text: res.answer,
        intent: res.intent,
        filters_used: res.filters_used || {},
        statistics: res.statistics || {},
        suggestions: res.suggestions || [],
        disclaimer: res.disclaimer,
        requires_confirmation: Boolean(res.requires_confirmation),
        action_blocked: Boolean(res.action_blocked),
        provider: res.provider || "deterministic",
        timestamp: new Date().toLocaleTimeString(),
      };
      setMessages((prev) => [...prev, botEntry]);
    } catch (err) {
      const msg = err.message || "AI Analytics Assistant unavailable";
      setErrorMsg(msg);
      onNotify && onNotify(msg, "error");
    } finally {
      setLoading(false);
    }
  };

  const sampleQuestions = aiStatus?.sample_questions || [
    "How many students are enrolled in each branch?",
    "Which courses have the lowest attendance?",
    "What is the average attendance for Semester 3?",
    "Summarize the academic performance of courses.",
    "Explain recent enrollment and attendance trends.",
    "Generate a concise narrative for the current filtered report.",
  ];

  return (
    <Paper
      elevation={0}
      sx={{
        p: 3,
        borderRadius: 3,
        border: "1px solid",
        borderColor: "divider",
      }}
    >
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          flexWrap: "wrap",
          gap: 1.5,
          mb: 2,
        }}
      >
        <Box>
          <Stack direction="row" spacing={1} alignItems="center">
            <AutoAwesomeRoundedIcon color="primary" />
            <Typography variant="h6" sx={{ fontWeight: 800 }}>
              AI Analytics Assistant
            </Typography>
            <Chip
              size="small"
              icon={<VerifiedUserRoundedIcon />}
              label="Grounded Aggregate Analytics • Zero PII Sent Externally"
              color="primary"
              variant="outlined"
              sx={{ fontWeight: 600 }}
            />
          </Stack>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            Ask natural-language questions about enrollment, attendance, and
            course performance. Answers are strictly grounded in deterministic
            database calculations scoped to your{" "}
            <strong>{currentUser?.role || "User"}</strong> permissions.
          </Typography>
        </Box>

        {messages.length > 0 && (
          <Button
            size="small"
            color="inherit"
            startIcon={<DeleteSweepRoundedIcon />}
            onClick={() => {
              setMessages([]);
              setErrorMsg("");
            }}
            sx={{ textTransform: "none" }}
          >
            Clear Session Chat
          </Button>
        )}
      </Box>

      {/* Starter Prompt Chips */}
      <Stack
        direction="row"
        spacing={1}
        flexWrap="wrap"
        useFlexGap
        sx={{ mb: 2 }}
      >
        {sampleQuestions.map((sq) => (
          <Chip
            key={sq}
            label={sq}
            size="small"
            clickable
            variant="outlined"
            onClick={() => handleAskQuestion(sq)}
            disabled={loading}
          />
        ))}
      </Stack>

      {/* Input Bar */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleAskQuestion();
        }}
      >
        <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
          <TextField
            size="small"
            fullWidth
            placeholder="Ask a question (e.g. Which courses have the lowest attendance?)"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            disabled={loading}
          />
          <Button
            type="submit"
            variant="contained"
            disabled={loading}
            endIcon={
              loading ? (
                <CircularProgress size={16} color="inherit" />
              ) : (
                <SendRoundedIcon />
              )
            }
            sx={{ textTransform: "none", fontWeight: 700, minWidth: 140 }}
          >
            {loading ? "Analyzing..." : "Ask Assistant"}
          </Button>
        </Stack>
      </form>

      {errorMsg && (
        <Alert severity="error" sx={{ mt: 2, borderRadius: 2 }}>
          {errorMsg}
        </Alert>
      )}

      {/* Session Chat History */}
      {messages.length > 0 && (
        <Stack spacing={2} sx={{ mt: 2.5 }}>
          {messages.map((m) =>
            m.sender === "user" ? (
              <Box
                key={m.id}
                sx={{
                  alignSelf: "flex-end",
                  bgcolor: "primary.main",
                  color: "#fff",
                  px: 2,
                  py: 1,
                  borderRadius: 2.5,
                  maxWidth: "85%",
                }}
              >
                <Typography variant="body2" sx={{ fontWeight: 600 }}>
                  {m.text}
                </Typography>
              </Box>
            ) : (
              <Paper
                key={m.id}
                variant="outlined"
                sx={{
                  p: 2,
                  borderRadius: 2.5,
                  bgcolor: "background.default",
                }}
              >
                {m.requires_confirmation && (
                  <Alert severity="warning" sx={{ mb: 1.5, borderRadius: 2 }}>
                    Explicit Confirmation Required — Read-Only Guard Active
                  </Alert>
                )}

                <Typography variant="body2" sx={{ mb: 1.5, lineHeight: 1.6 }}>
                  {m.text}
                </Typography>

                {/* Active Filters & Grounding Metadata */}
                <Stack
                  direction="row"
                  spacing={1}
                  flexWrap="wrap"
                  useFlexGap
                  sx={{ mb: 1 }}
                >
                  <Chip
                    size="small"
                    label={`Intent: ${m.intent}`}
                    color="info"
                    variant="outlined"
                  />
                  {Object.entries(m.filters_used || {})
                    .filter(([, val]) => val && val !== "All")
                    .map(([k, val]) => (
                      <Chip
                        key={k}
                        size="small"
                        label={`${k}: ${val}`}
                        variant="outlined"
                      />
                    ))}
                </Stack>

                {/* Grounding Statistics Explanation */}
                {m.statistics && Object.keys(m.statistics).length > 0 && (
                  <Box
                    sx={{
                      p: 1.25,
                      mt: 1,
                      borderRadius: 1.5,
                      bgcolor: "action.hover",
                      fontFamily: "monospace",
                      fontSize: "0.75rem",
                      overflowX: "auto",
                    }}
                  >
                    <Typography
                      variant="caption"
                      sx={{ fontWeight: 700, display: "block", mb: 0.5 }}
                    >
                      Verified Deterministic Statistics Used:
                    </Typography>
                    {JSON.stringify(m.statistics)}
                  </Box>
                )}

                {m.disclaimer && (
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    sx={{ display: "block", mt: 1, fontStyle: "italic" }}
                  >
                    {m.disclaimer}
                  </Typography>
                )}
              </Paper>
            )
          )}
        </Stack>
      )}
    </Paper>
  );
}

// =========================================================
// 2. ADVANCED ANALYTICS WORKSPACE (/analytics)
// =========================================================
export function AdvancedAnalyticsWorkspace({
  students = [],
  currentUser,
  onNotify,
}) {
  const [filters, setFilters] = useState({
    branch: "",
    semester: "",
    academic_year: "",
    course_code: "",
    date_from: "",
    date_to: "",
  });
  const [courses, setCourses] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState("");

  const loadAnalytics = useCallback(
    async (activeFilters = filters) => {
      setLoading(true);
      setErrorMsg("");
      try {
        const [crs, data] = await Promise.all([
          getCourses(false),
          getAdvancedAnalyticsApi(activeFilters),
        ]);
        setCourses(crs);
        setAnalytics(data);
      } catch (err) {
        const msg = err.message || "Failed to load advanced analytics";
        setErrorMsg(msg);
        onNotify && onNotify(msg, "error");
      } finally {
        setLoading(false);
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [onNotify]
  );

  useEffect(() => {
    loadAnalytics(filters);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const distinctBranches = Array.from(
    new Set(students.map((s) => s.branch).filter(Boolean))
  ).sort();

  const totals = analytics?.totals || {};
  const attSum = analytics?.attendance_summary || {};
  const gpaSum = analytics?.gpa_summary || {};
  const branchData = analytics?.enrollment_by_branch || [];
  const semData = analytics?.enrollment_by_semester || [];
  const gradeDist = analytics?.grade_distribution || [];
  const coursePerf = analytics?.course_performance || [];
  const attTrends = analytics?.attendance_trends || [];

  return (
    <Stack spacing={3}>
      {/* Multi-field & Date-Range Filter Bar */}
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
          Multi-Field & Date-Range Analytics Filters
        </Typography>
        <Grid container spacing={1.5} alignItems="center">
          <Grid size={{ xs: 12, sm: 4, md: 2 }}>
            <TextField
              select
              size="small"
              label="Branch"
              fullWidth
              value={filters.branch}
              onChange={(e) =>
                setFilters((p) => ({ ...p, branch: e.target.value }))
              }
            >
              <MenuItem value="">All Branches</MenuItem>
              {distinctBranches.map((b) => (
                <MenuItem key={b} value={b}>
                  {b}
                </MenuItem>
              ))}
            </TextField>
          </Grid>

          <Grid size={{ xs: 12, sm: 4, md: 1.5 }}>
            <TextField
              select
              size="small"
              label="Semester"
              fullWidth
              value={filters.semester}
              onChange={(e) =>
                setFilters((p) => ({ ...p, semester: e.target.value }))
              }
            >
              <MenuItem value="">All</MenuItem>
              {["1", "2", "3", "4", "5", "6", "7", "8"].map((sem) => (
                <MenuItem key={sem} value={sem}>
                  Sem {sem}
                </MenuItem>
              ))}
            </TextField>
          </Grid>

          <Grid size={{ xs: 12, sm: 4, md: 2 }}>
            <TextField
              select
              size="small"
              label="Course"
              fullWidth
              value={filters.course_code}
              onChange={(e) =>
                setFilters((p) => ({ ...p, course_code: e.target.value }))
              }
            >
              <MenuItem value="">All Courses</MenuItem>
              {courses.map((c) => (
                <MenuItem key={c.course_code} value={c.course_code}>
                  {c.course_code} — {c.course_name}
                </MenuItem>
              ))}
            </TextField>
          </Grid>

          <Grid size={{ xs: 12, sm: 6, md: 2 }}>
            <TextField
              size="small"
              type="date"
              label="Date From"
              fullWidth
              value={filters.date_from}
              onChange={(e) =>
                setFilters((p) => ({ ...p, date_from: e.target.value }))
              }
              slotProps={{ inputLabel: { shrink: true } }}
            />
          </Grid>

          <Grid size={{ xs: 12, sm: 6, md: 2 }}>
            <TextField
              size="small"
              type="date"
              label="Date To"
              fullWidth
              value={filters.date_to}
              onChange={(e) =>
                setFilters((p) => ({ ...p, date_to: e.target.value }))
              }
              slotProps={{ inputLabel: { shrink: true } }}
            />
          </Grid>

          <Grid size={{ xs: 12, md: 2.5 }}>
            <Stack direction="row" spacing={1}>
              <Button
                variant="contained"
                size="small"
                fullWidth
                startIcon={<FilterAltRoundedIcon />}
                onClick={() => loadAnalytics(filters)}
                sx={{ textTransform: "none", fontWeight: 700 }}
              >
                Apply
              </Button>
              <Button
                variant="outlined"
                size="small"
                startIcon={<RestartAltRoundedIcon />}
                onClick={() => {
                  const empty = {
                    branch: "",
                    semester: "",
                    academic_year: "",
                    course_code: "",
                    date_from: "",
                    date_to: "",
                  };
                  setFilters(empty);
                  loadAnalytics(empty);
                }}
                sx={{ textTransform: "none" }}
              >
                Reset
              </Button>
            </Stack>
          </Grid>
        </Grid>
      </Paper>

      {loading && <LinearProgress />}
      {errorMsg && <Alert severity="error">{errorMsg}</Alert>}

      {/* Summary KPI Cards */}
      <Grid container spacing={2}>
        {[
          {
            label: "Scoped Students",
            value: totals.total_students ?? 0,
            sub: `Role Scope: ${analytics?.role_scope || currentUser?.role || "Admin"}`,
          },
          {
            label: "Active Courses & Enrollments",
            value: `${totals.total_courses ?? 0} / ${totals.total_enrollments ?? 0}`,
            sub: "Courses / Active Student Enrollments",
          },
          {
            label: "Overall Session Attendance",
            value: `${attSum.attendance_percentage ?? 0}%`,
            sub: `${attSum.below_threshold_count ?? 0} Below ${attSum.min_attendance_threshold ?? 75}% Threshold`,
          },
          {
            label: "Credit-Weighted Avg CGPA",
            value:
              gpaSum.average_cgpa !== null && gpaSum.average_cgpa !== undefined
                ? `${gpaSum.average_cgpa} / ${gpaSum.max_grade_points || 10}`
                : "N/A",
            sub: gpaSum.scale_name || "Standard 10-Point CBCS Scale",
          },
        ].map((kpi) => (
          <Grid size={{ xs: 12, sm: 6, md: 3 }} key={kpi.label}>
            <Paper
              elevation={0}
              sx={{
                p: 2.5,
                borderRadius: 3,
                border: "1px solid",
                borderColor: "divider",
              }}
            >
              <Typography variant="caption" color="text.secondary">
                {kpi.label}
              </Typography>
              <Typography variant="h5" sx={{ fontWeight: 800, my: 0.5 }}>
                {kpi.value}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {kpi.sub}
              </Typography>
            </Paper>
          </Grid>
        ))}
      </Grid>

      {/* Charts Row: Branch Enrollment & Grade Distribution */}
      <Grid container spacing={2.5}>
        <Grid size={{ xs: 12, md: 6 }}>
          <Paper
            elevation={0}
            sx={{
              p: 2.5,
              borderRadius: 3,
              border: "1px solid",
              borderColor: "divider",
              height: 340,
            }}
          >
            <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 1.5 }}>
              Branch-Wise Student Enrollment
            </Typography>
            {branchData.length === 0 ? (
              <Typography variant="body2" color="text.secondary" sx={{ py: 8, textAlign: "center" }}>
                No branch enrollment data available for current filters.
              </Typography>
            ) : (
              <ResponsiveContainer width="100%" height="85%">
                <BarChart data={branchData}>
                  <CartesianGrid strokeDasharray="3 3" opacity={0.25} />
                  <XAxis dataKey="branch" />
                  <YAxis allowDecimals={false} />
                  <RechartsTooltip />
                  <Legend />
                  <Bar
                    dataKey="student_count"
                    name="Enrolled Students"
                    fill="#2563eb"
                    radius={[6, 6, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            )}
          </Paper>
        </Grid>

        <Grid size={{ xs: 12, md: 6 }}>
          <Paper
            elevation={0}
            sx={{
              p: 2.5,
              borderRadius: 3,
              border: "1px solid",
              borderColor: "divider",
              height: 340,
            }}
          >
            <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 1.5 }}>
              Assessment Grade Distribution ({gpaSum.scale_name || "Active Scale"})
            </Typography>
            <ResponsiveContainer width="100%" height="85%">
              <BarChart data={gradeDist}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.25} />
                <XAxis dataKey="letter_grade" />
                <YAxis allowDecimals={false} />
                <RechartsTooltip />
                <Legend />
                <Bar
                  dataKey="count"
                  name="Assessments Count"
                  fill="#4f46e5"
                  radius={[6, 6, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>
      </Grid>

      {/* Course Performance Comparison & Attendance Trend */}
      <Grid container spacing={2.5}>
        <Grid size={{ xs: 12, lg: 7 }}>
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
              Course Performance & Attendance Comparison
            </Typography>
            {coursePerf.length === 0 ? (
              <Typography variant="body2" color="text.secondary" sx={{ py: 3, textAlign: "center" }}>
                No course performance records available for the selected filters.
              </Typography>
            ) : (
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 700 }}>Course</TableCell>
                    <TableCell sx={{ fontWeight: 700 }}>Branch</TableCell>
                    <TableCell sx={{ fontWeight: 700 }}>Enrolled</TableCell>
                    <TableCell sx={{ fontWeight: 700 }}>Avg Marks (%)</TableCell>
                    <TableCell sx={{ fontWeight: 700 }}>Pass Rate</TableCell>
                    <TableCell sx={{ fontWeight: 700 }}>Attendance (%)</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {coursePerf.map((cp) => (
                    <TableRow key={cp.course_code} hover>
                      <TableCell sx={{ fontWeight: 600 }}>
                        {cp.course_code} — {cp.course_name}
                      </TableCell>
                      <TableCell>{cp.branch}</TableCell>
                      <TableCell>{cp.enrolled_count}</TableCell>
                      <TableCell>
                        {cp.average_percentage !== null
                          ? `${cp.average_percentage}%`
                          : "N/A"}
                      </TableCell>
                      <TableCell>
                        {cp.pass_rate !== null ? `${cp.pass_rate}%` : "N/A"}
                      </TableCell>
                      <TableCell>
                        {cp.attendance_percentage !== null
                          ? `${cp.attendance_percentage}%`
                          : "N/A"}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </Paper>
        </Grid>

        <Grid size={{ xs: 12, lg: 5 }}>
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
              Semester Enrollment & Attendance Date Trends
            </Typography>
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mb: 2 }}>
              {semData.map((s) => (
                <Chip
                  key={s.semester}
                  label={`${s.semester}: ${s.student_count} student(s)`}
                  size="small"
                  color="primary"
                  variant="outlined"
                />
              ))}
            </Stack>
            <Divider sx={{ mb: 1.5 }} />
            {attTrends.length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                No session attendance dates logged in this filter window.
              </Typography>
            ) : (
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 700 }}>Date</TableCell>
                    <TableCell sx={{ fontWeight: 700 }}>P / L / A / E</TableCell>
                    <TableCell sx={{ fontWeight: 700 }}>Attendance (%)</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {attTrends.slice(-8).map((t) => (
                    <TableRow key={t.date}>
                      <TableCell sx={{ fontFamily: "monospace" }}>
                        {t.date}
                      </TableCell>
                      <TableCell>
                        {t.present} / {t.late} / {t.absent} / {t.excused}
                      </TableCell>
                      <TableCell sx={{ fontWeight: 700 }}>
                        {t.attendance_percentage}%
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </Paper>
        </Grid>
      </Grid>

      {/* Integrated AI Analytics Assistant */}
      <AiAnalyticsAssistantPanel
        activeFilters={filters}
        currentUser={currentUser}
        onNotify={onNotify}
      />
    </Stack>
  );
}

// =========================================================
// 3. REPORTS & EXPORTS WORKSPACE (/reports)
// =========================================================
export function ReportsAndExportsWorkspace({
  students = [],
  currentUser,
  onNotify,
}) {
  const userRole = currentUser?.role || "Admin";
  const allowedReportTypes = REPORT_TYPES.filter((rt) =>
    rt.roles.includes(userRole)
  );

  const [filters, setFilters] = useState({
    report_type: "student_directory",
    branch: "",
    semester: "",
    academic_year: "",
    course_code: "",
    date_from: "",
    date_to: "",
    limit: 500,
  });

  const [courses, setCourses] = useState([]);
  const [preview, setPreview] = useState(null);
  const [loadingPreview, setLoadingPreview] = useState(true);
  const [exportingFormat, setExportingFormat] = useState("");
  const [errorMsg, setErrorMsg] = useState("");

  const loadPreview = useCallback(
    async (activeFilters = filters) => {
      setLoadingPreview(true);
      setErrorMsg("");
      try {
        const [crs, prevData] = await Promise.all([
          getCourses(false),
          getReportPreviewApi(activeFilters),
        ]);
        setCourses(crs);
        setPreview(prevData);
      } catch (err) {
        const msg = err.message || "Failed to load report preview";
        setErrorMsg(msg);
        onNotify && onNotify(msg, "error");
      } finally {
        setLoadingPreview(false);
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [onNotify]
  );

  useEffect(() => {
    loadPreview(filters);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleExport = async (format) => {
    setExportingFormat(format);
    setErrorMsg("");
    try {
      const res = await downloadReportExportApi({ ...filters, format });
      onNotify &&
        onNotify(
          `Downloaded ${format.toUpperCase()} report: ${res.filename}`,
          "success"
        );
    } catch (err) {
      const msg = err.message || `Failed to export ${format.toUpperCase()}`;
      setErrorMsg(msg);
      onNotify && onNotify(msg, "error");
    } finally {
      setExportingFormat("");
    }
  };

  const distinctBranches = Array.from(
    new Set(students.map((s) => s.branch).filter(Boolean))
  ).sort();

  const columns = preview?.columns || [];
  const rows = preview?.rows || [];
  const summaryMetrics = preview?.summary_metrics || [];

  return (
    <Stack spacing={3}>
      {/* Report Configuration & Export Bar */}
      <Paper
        elevation={0}
        sx={{
          p: 3,
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
            mb: 2.5,
          }}
        >
          <Box>
            <Typography variant="h6" sx={{ fontWeight: 800 }}>
              Report Builder, Live Preview & Multi-Format Exports
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Select a report type, apply academic and date-range filters,
              preview the verified records, and export to PDF, Excel (.xlsx), or
              CSV.
            </Typography>
          </Box>

          <Stack direction="row" spacing={1.25} flexWrap="wrap" useFlexGap>
            <Button
              variant="contained"
              color="error"
              startIcon={<PictureAsPdfRoundedIcon />}
              disabled={Boolean(exportingFormat)}
              onClick={() => handleExport("pdf")}
              sx={{ textTransform: "none", fontWeight: 700 }}
            >
              {exportingFormat === "pdf" ? "Generating PDF..." : "Export PDF"}
            </Button>

            <Button
              variant="contained"
              color="success"
              startIcon={<TableViewRoundedIcon />}
              disabled={Boolean(exportingFormat)}
              onClick={() => handleExport("xlsx")}
              sx={{ textTransform: "none", fontWeight: 700 }}
            >
              {exportingFormat === "xlsx"
                ? "Building Workbook..."
                : "Export Excel (.xlsx)"}
            </Button>

            <Button
              variant="outlined"
              startIcon={<FileDownloadRoundedIcon />}
              disabled={Boolean(exportingFormat)}
              onClick={() => handleExport("csv")}
              sx={{ textTransform: "none", fontWeight: 700 }}
            >
              {exportingFormat === "csv" ? "Exporting CSV..." : "Export CSV"}
            </Button>
          </Stack>
        </Box>

        <Grid container spacing={1.5} alignItems="center">
          <Grid size={{ xs: 12, md: 3.5 }}>
            <TextField
              select
              size="small"
              label="Report Type"
              fullWidth
              value={filters.report_type}
              onChange={(e) => {
                const updated = { ...filters, report_type: e.target.value };
                setFilters(updated);
                loadPreview(updated);
              }}
            >
              {allowedReportTypes.map((rt) => (
                <MenuItem key={rt.value} value={rt.value}>
                  {rt.label}
                </MenuItem>
              ))}
            </TextField>
          </Grid>

          <Grid size={{ xs: 12, sm: 4, md: 1.5 }}>
            <TextField
              select
              size="small"
              label="Branch"
              fullWidth
              value={filters.branch}
              onChange={(e) =>
                setFilters((p) => ({ ...p, branch: e.target.value }))
              }
            >
              <MenuItem value="">All</MenuItem>
              {distinctBranches.map((b) => (
                <MenuItem key={b} value={b}>
                  {b}
                </MenuItem>
              ))}
            </TextField>
          </Grid>

          <Grid size={{ xs: 12, sm: 4, md: 1.5 }}>
            <TextField
              select
              size="small"
              label="Semester"
              fullWidth
              value={filters.semester}
              onChange={(e) =>
                setFilters((p) => ({ ...p, semester: e.target.value }))
              }
            >
              <MenuItem value="">All</MenuItem>
              {["1", "2", "3", "4", "5", "6", "7", "8"].map((sem) => (
                <MenuItem key={sem} value={sem}>
                  Sem {sem}
                </MenuItem>
              ))}
            </TextField>
          </Grid>

          <Grid size={{ xs: 12, sm: 4, md: 2 }}>
            <TextField
              select
              size="small"
              label="Course"
              fullWidth
              value={filters.course_code}
              onChange={(e) =>
                setFilters((p) => ({ ...p, course_code: e.target.value }))
              }
            >
              <MenuItem value="">All Courses</MenuItem>
              {courses.map((c) => (
                <MenuItem key={c.course_code} value={c.course_code}>
                  {c.course_code}
                </MenuItem>
              ))}
            </TextField>
          </Grid>

          <Grid size={{ xs: 6, sm: 4, md: 1.75 }}>
            <TextField
              size="small"
              type="date"
              label="Date From"
              fullWidth
              value={filters.date_from}
              onChange={(e) =>
                setFilters((p) => ({ ...p, date_from: e.target.value }))
              }
              slotProps={{ inputLabel: { shrink: true } }}
            />
          </Grid>

          <Grid size={{ xs: 6, sm: 4, md: 1.75 }}>
            <Stack direction="row" spacing={1}>
              <Button
                variant="contained"
                size="small"
                fullWidth
                onClick={() => loadPreview(filters)}
                sx={{ textTransform: "none", fontWeight: 700 }}
              >
                Preview
              </Button>
            </Stack>
          </Grid>
        </Grid>
      </Paper>

      {(loadingPreview || exportingFormat) && <LinearProgress />}
      {errorMsg && <Alert severity="error">{errorMsg}</Alert>}

      {/* Report Preview Table & Summary Metrics */}
      <Paper
        elevation={0}
        sx={{
          p: 3,
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
          <Box>
            <Typography variant="subtitle1" sx={{ fontWeight: 800 }}>
              {preview?.title || "Report Preview"}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Generated At: {preview?.generated_at || "-"} • Scope:{" "}
              {preview?.generated_by || userRole} • Showing {rows.length} row(s)
            </Typography>
          </Box>

          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            {summaryMetrics.map((m) => (
              <Chip
                key={m.label}
                label={`${m.label}: ${m.value}`}
                color="primary"
                variant="outlined"
                size="small"
                sx={{ fontWeight: 700 }}
              />
            ))}
          </Stack>
        </Box>

        <Divider sx={{ mb: 2 }} />

        {rows.length === 0 ? (
          <Typography
            variant="body2"
            color="text.secondary"
            sx={{ py: 5, textAlign: "center" }}
          >
            No records matched the selected report filters. Adjust the filters
            above and click Preview.
          </Typography>
        ) : (
          <Box sx={{ overflowX: "auto" }}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  {columns.map((c) => (
                    <TableCell key={c.key} sx={{ fontWeight: 700 }}>
                      {c.label}
                    </TableCell>
                  ))}
                </TableRow>
              </TableHead>
              <TableBody>
                {rows.slice(0, 50).map((r, idx) => (
                  <TableRow key={idx} hover>
                    {columns.map((c) => (
                      <TableCell key={c.key}>
                        {r[c.key] !== null && r[c.key] !== undefined
                          ? String(r[c.key])
                          : ""}
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Box>
        )}
      </Paper>

      {/* AI Assistant Panel for Report Narrative & Q&A */}
      <AiAnalyticsAssistantPanel
        activeFilters={filters}
        currentUser={currentUser}
        onNotify={onNotify}
      />
    </Stack>
  );
}

