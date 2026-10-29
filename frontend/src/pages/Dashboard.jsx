import React, { useState, useEffect, useMemo, useCallback } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  Box,
  Typography,
  Button,
  Paper,
  Grid,
  Chip,
  Stack,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Drawer,
  Divider,
  Snackbar,
  Alert,
  Avatar,
  IconButton,
  Switch,
  FormControlLabel,
  TextField,
} from "@mui/material";
import PersonAddAlt1RoundedIcon from "@mui/icons-material/PersonAddAlt1Rounded";
import FileUploadRoundedIcon from "@mui/icons-material/FileUploadRounded";
import RefreshRoundedIcon from "@mui/icons-material/RefreshRounded";
import DeleteSweepRoundedIcon from "@mui/icons-material/DeleteSweepRounded";
import CloseRoundedIcon from "@mui/icons-material/CloseRounded";
import EditRoundedIcon from "@mui/icons-material/EditRounded";
import CheckCircleOutlineRoundedIcon from "@mui/icons-material/CheckCircleOutlineRounded";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";

import {
  API,
  getStudents,
  addStudent,
  deleteStudent,
  updateStudent,
  bulkDeleteStudents,
  bulkImportStudents,
  getActivityLogs,
  clearActivityLogs,
  recordActivityLog,
  checkHealth,
  resetPassword,
  createPlatformUser,
} from "../services/api";

import DashboardCards from "../components/DashboardCards";
import SearchStudent from "../components/SearchStudent";
import StudentForm from "../components/StudentForm";
import StudentTable from "../components/StudentTable";
import {
  AcademicsWorkspace,
  AttendanceWorkspace,
  PerformanceWorkspace,
} from "../components/AcademicModules";
import {
  AdvancedAnalyticsWorkspace,
  ReportsAndExportsWorkspace,
} from "../components/ReportingAndAiModules";
import "./Dashboard.css";

const CHART_COLORS = [
  "#2563eb",
  "#4f46e5",
  "#0284c7",
  "#0d9488",
  "#7c3aed",
  "#ea580c",
  "#db2777",
  "#16a34a",
];

// Helper to export an array of objects to CSV
const downloadCsv = (filename, rows, headers) => {
  const escapeCsvCell = (val) => {
    const str = val === null || val === undefined ? "" : String(val);
    if (/[",\n]/.test(str)) {
      return `"${str.replace(/"/g, '""')}"`;
    }
    return str;
  };

  const csvContent = [
    headers.map((h) => escapeCsvCell(h.label)).join(","),
    ...rows.map((r) => headers.map((h) => escapeCsvCell(r[h.key])).join(",")),
  ].join("\n");

  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.setAttribute("download", filename);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
};

// Parse simple CSV text into student objects
const parseCsvText = (csvText) => {
  const lines = String(csvText || "")
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter(Boolean);

  if (lines.length < 2) return [];

  const rawHeaders = lines[0]
    .split(",")
    .map((h) => h.replace(/^"|"$/g, "").trim().toLowerCase());

  const parsed = [];
  for (let i = 1; i < lines.length; i += 1) {
    const cols = lines[i]
      .split(",")
      .map((c) => c.replace(/^"|"$/g, "").trim());
    const rowObj = {};
    rawHeaders.forEach((h, idx) => {
      rowObj[h] = cols[idx] ?? "";
    });

    parsed.push({
      reg_no: rowObj.reg_no || rowObj["registration number"] || rowObj.regno || "",
      roll_no: rowObj.roll_no || rowObj["roll number"] || rowObj.rollno || "",
      name: rowObj.name || rowObj["student name"] || "",
      age: Number(rowObj.age || 0),
      branch: rowObj.branch || rowObj.department || "",
      email: rowObj.email || "",
      phone: rowObj.phone || "",
      semester: rowObj.semester || "1",
      status: rowObj.status || "Active",
      gpa: rowObj.gpa !== undefined && rowObj.gpa !== "" ? Number(rowObj.gpa) : "",
      attendance_pct:
        rowObj.attendance_pct !== undefined && rowObj.attendance_pct !== ""
          ? Number(rowObj.attendance_pct)
          : "",
    });
  }
  return parsed;
};

export default function Dashboard({
  currentUser = { username: "admin", role: "Admin", full_name: "System Administrator" },
  globalSearch = "",
  onGlobalSearchChange,
  darkMode = false,
  onToggleDarkMode,
  onLogsUpdated,
  onApiStatusChange,
}) {
  const location = useLocation();
  const navigate = useNavigate();
  const rawPathname = location.pathname || "/";
  const firstSegment = "/" + (rawPathname.split("/").filter(Boolean)[0] || "");
  const activePath = [
    "/students",
    "/academics",
    "/attendance",
    "/performance",
    "/analytics",
    "/reports",
    "/logs",
    "/settings",
  ].includes(firstSegment)
    ? firstSegment
    : "/";

  const userRole = currentUser?.role || "Admin";
  const isAdmin = userRole === "Admin";
  const isFaculty = userRole === "Faculty";
  const canEdit = isAdmin || isFaculty;

  // Password reset state in Settings
  const [pwdForm, setPwdForm] = useState({
    current_password: "",
    new_password: "",
  });

  // New user provisioning state (Admin only)
  const [newUserForm, setNewUserForm] = useState({
    username: "",
    password: "",
    role: "Student",
    full_name: "",
    assigned_branches: "CSE",
    linked_reg_no: "",
  });

  // Core data state
  const [students, setStudents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  // Search, filter, sort, pagination state
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [branchFilter, setBranchFilter] = useState("All");
  const [statusFilter, setStatusFilter] = useState("All");
  const [semesterFilter, setSemesterFilter] = useState("All");
  const [sortBy, setSortBy] = useState("reg_no");
  const [sortOrder, setSortOrder] = useState("asc");
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);

  // Selection state for bulk operations
  const [selectedIds, setSelectedIds] = useState([]);

  // Modal & Drawer state
  const [formOpen, setFormOpen] = useState(false);
  const [editingStudent, setEditingStudent] = useState(null);
  const [profileStudent, setProfileStudent] = useState(null);
  const [deleteDialog, setDeleteDialog] = useState({
    open: false,
    mode: "single", // 'single' | 'bulk'
    targetRegNo: null,
    targetName: "",
  });

  // CSV Import Modal state
  const [importOpen, setImportOpen] = useState(false);
  const [csvText, setCsvText] = useState("");
  const [csvPreview, setCsvPreview] = useState([]);

  // Activity logs state
  const [logs, setLogs] = useState(() => getActivityLogs());

  // Toast notification state
  const [toast, setToast] = useState({
    open: false,
    message: "",
    severity: "success",
  });

  const showToast = useCallback((message, severity = "success") => {
    setToast({ open: true, message, severity });
  }, []);

  const refreshLogs = useCallback(() => {
    const updated = getActivityLogs();
    setLogs(updated);
    if (onLogsUpdated) onLogsUpdated(updated);
  }, [onLogsUpdated]);

  // Sync top-bar global search with local searchQuery
  useEffect(() => {
    if (globalSearch !== undefined && globalSearch !== searchQuery) {
      setSearchQuery(globalSearch);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [globalSearch]);

  // Debounce search query (250ms)
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchQuery);
      setPage(0);
    }, 250);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Load students from API
  const loadStudents = useCallback(
    async (silent = false) => {
      if (!silent) setLoading(true);
      try {
        const data = await getStudents();
        setStudents(Array.isArray(data) ? data : []);
        if (onApiStatusChange) onApiStatusChange(true);
      } catch (error) {
        if (onApiStatusChange) onApiStatusChange(false);
        showToast(error.message || "Failed to load students", "error");
      } finally {
        setLoading(false);
      }
    },
    [onApiStatusChange, showToast]
  );

  useEffect(() => {
    loadStudents();
  }, [loadStudents]);

  // Distinct branches from real student records
  const branches = useMemo(() => {
    const set = new Set(
      students.map((s) => (s.branch || "").trim()).filter(Boolean)
    );
    return Array.from(set).sort();
  }, [students]);

  // Filtered and sorted students
  const filteredStudents = useMemo(() => {
    const q = debouncedSearch.trim().toLowerCase();

    const filtered = students.filter((s) => {
      if (branchFilter !== "All" && s.branch !== branchFilter) return false;
      const st = s.status || "Active";
      if (statusFilter !== "All" && st !== statusFilter) return false;
      if (
        semesterFilter !== "All" &&
        String(s.semester || "") !== semesterFilter
      ) {
        return false;
      }

      if (!q) return true;
      return (
        String(s.reg_no || "").toLowerCase().includes(q) ||
        String(s.roll_no || "").toLowerCase().includes(q) ||
        String(s.name || "").toLowerCase().includes(q) ||
        String(s.branch || "").toLowerCase().includes(q) ||
        String(s.email || "").toLowerCase().includes(q)
      );
    });

    return [...filtered].sort((a, b) => {
      let valA = a[sortBy];
      let valB = b[sortBy];

      if (sortBy === "age" || sortBy === "gpa" || sortBy === "attendance_pct") {
        valA = Number(valA ?? -1);
        valB = Number(valB ?? -1);
      } else {
        valA = String(valA ?? "").toLowerCase();
        valB = String(valB ?? "").toLowerCase();
      }

      if (valA < valB) return sortOrder === "asc" ? -1 : 1;
      if (valA > valB) return sortOrder === "asc" ? 1 : -1;
      return 0;
    });
  }, [
    students,
    debouncedSearch,
    branchFilter,
    statusFilter,
    semesterFilter,
    sortBy,
    sortOrder,
  ]);

  // Paginated slice
  const paginatedStudents = useMemo(() => {
    const start = page * rowsPerPage;
    return filteredStudents.slice(start, start + rowsPerPage);
  }, [filteredStudents, page, rowsPerPage]);

  // Real-time Analytics computed strictly from MongoDB records
  const analyticsData = useMemo(() => {
    const branchMap = {};
    const statusMap = {};
    const ageMap = {};

    students.forEach((s) => {
      const b = (s.branch || "Unassigned").trim();
      branchMap[b] = (branchMap[b] || 0) + 1;

      const st = s.status || "Active";
      statusMap[st] = (statusMap[st] || 0) + 1;

      const ageGroup = s.age ? `${s.age} yrs` : "N/A";
      ageMap[ageGroup] = (ageMap[ageGroup] || 0) + 1;
    });

    const branchChart = Object.entries(branchMap)
      .map(([branch, count]) => ({ branch, count }))
      .sort((a, b) => b.count - a.count);

    const statusChart = Object.entries(statusMap).map(([name, value]) => ({
      name,
      value,
    }));

    const ageChart = Object.entries(ageMap)
      .map(([age, count]) => ({ age, count }))
      .sort((a, b) => parseInt(a.age, 10) - parseInt(b.age, 10));

    return { branchChart, statusChart, ageChart };
  }, [students]);

  // Handlers
  const handleSearchChange = (val) => {
    setSearchQuery(val);
    if (onGlobalSearchChange) onGlobalSearchChange(val);
  };

  const handleResetFilters = () => {
    setSearchQuery("");
    if (onGlobalSearchChange) onGlobalSearchChange("");
    setBranchFilter("All");
    setStatusFilter("All");
    setSemesterFilter("All");
    setPage(0);
  };

  const handleRequestSort = (property) => {
    const isAsc = sortBy === property && sortOrder === "asc";
    setSortOrder(isAsc ? "desc" : "asc");
    setSortBy(property);
  };

  const handleSelectOne = (regNo) => {
    setSelectedIds((prev) =>
      prev.includes(regNo) ? prev.filter((id) => id !== regNo) : [...prev, regNo]
    );
  };

  const handleSelectAll = (ids) => {
    setSelectedIds(ids);
  };

  const handleOpenAdd = () => {
    setEditingStudent(null);
    setFormOpen(true);
  };

  const handleOpenEdit = (student) => {
    setEditingStudent(student);
    setFormOpen(true);
  };

  const handleFormSubmit = async (formData) => {
    setSubmitting(true);
    try {
      if (editingStudent) {
        await updateStudent(editingStudent.reg_no, formData);
        showToast(`Updated ${formData.name} (${editingStudent.reg_no})`, "success");
      } else {
        await addStudent(formData);
        showToast(`Enrolled ${formData.name} (${formData.reg_no})`, "success");
      }
      setFormOpen(false);
      setEditingStudent(null);
      refreshLogs();
      await loadStudents(true);
    } finally {
      setSubmitting(false);
    }
  };

  const handleConfirmDeleteRequest = (regNo, studentObj) => {
    setDeleteDialog({
      open: true,
      mode: "single",
      targetRegNo: regNo,
      targetName: studentObj?.name || regNo,
    });
  };

  const handleConfirmBulkDeleteRequest = () => {
    if (selectedIds.length === 0) return;
    setDeleteDialog({
      open: true,
      mode: "bulk",
      targetRegNo: null,
      targetName: `${selectedIds.length} selected student(s)`,
    });
  };

  const handleExecuteDelete = async () => {
    setSubmitting(true);
    try {
      if (deleteDialog.mode === "bulk") {
        const res = await bulkDeleteStudents(selectedIds);
        showToast(res.message || "Selected students deleted", "info");
        setSelectedIds([]);
      } else if (deleteDialog.targetRegNo) {
        await deleteStudent(deleteDialog.targetRegNo);
        showToast(`Deleted student ${deleteDialog.targetRegNo}`, "info");
        setSelectedIds((prev) =>
          prev.filter((id) => id !== deleteDialog.targetRegNo)
        );
        if (profileStudent?.reg_no === deleteDialog.targetRegNo) {
          setProfileStudent(null);
        }
      }
      setDeleteDialog({ open: false, mode: "single", targetRegNo: null, targetName: "" });
      refreshLogs();
      await loadStudents(true);
    } catch (error) {
      showToast(error.message || "Delete operation failed", "error");
    } finally {
      setSubmitting(false);
    }
  };

  const handleExportCsv = (customRows = null, filename = "students_export.csv") => {
    const targetRows = Array.isArray(customRows) ? customRows : filteredStudents;
    if (targetRows.length === 0) {
      showToast("No student records available to export", "warning");
      return;
    }

    const headers = [
      { key: "reg_no", label: "Registration No" },
      { key: "roll_no", label: "Roll No" },
      { key: "name", label: "Student Name" },
      { key: "age", label: "Age" },
      { key: "branch", label: "Branch" },
      { key: "status", label: "Status" },
      { key: "semester", label: "Semester" },
      { key: "email", label: "Email" },
      { key: "phone", label: "Phone" },
      { key: "gpa", label: "GPA" },
      { key: "attendance_pct", label: "Attendance (%)" },
    ];

    downloadCsv(filename, targetRows, headers);
    recordActivityLog(
      "CSV Export",
      `Exported ${targetRows.length} student record(s) to ${filename}`,
      "info"
    );
    refreshLogs();
    showToast(`Exported ${targetRows.length} student record(s)`, "success");
  };

  const handleCsvFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (evt) => {
      const content = String(evt.target?.result || "");
      setCsvText(content);
      setCsvPreview(parseCsvText(content));
    };
    reader.readAsText(file);
  };

  const handleExecuteImport = async () => {
    if (csvPreview.length === 0) {
      showToast("Please provide valid CSV rows first", "warning");
      return;
    }
    setSubmitting(true);
    try {
      const res = await bulkImportStudents(csvPreview);
      showToast(
        `Imported ${res.added} student(s)${
          res.skipped ? `, skipped ${res.skipped}` : ""
        }`,
        res.added > 0 ? "success" : "warning"
      );
      setImportOpen(false);
      setCsvText("");
      setCsvPreview([]);
      refreshLogs();
      await loadStudents(true);
    } catch (err) {
      showToast(err.message || "CSV Import failed", "error");
    } finally {
      setSubmitting(false);
    }
  };

  // ==========================================
  // SECTION RENDERERS
  // ==========================================

  const renderOverviewSection = () => (
    <Box>
      <DashboardCards students={students} loading={loading} />

      {/* Charts Row */}
      <Grid container spacing={2.5} sx={{ mb: 3 }}>
        <Grid size={{ xs: 12, lg: 7 }}>
          <Paper
            elevation={0}
            sx={{
              p: 2.5,
              borderRadius: 3,
              border: "1px solid",
              borderColor: "divider",
              height: 360,
              display: "flex",
              flexDirection: "column",
            }}
          >
            <Box
              sx={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                mb: 2,
              }}
            >
              <Box>
                <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
                  Branch-wise Enrollment Distribution
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Live student count aggregated by academic department
                </Typography>
              </Box>
              <Chip
                size="small"
                label={`${branches.length} Active Branches`}
                color="primary"
                variant="outlined"
              />
            </Box>

            <Box sx={{ flex: 1, minHeight: 250 }}>
              {analyticsData.branchChart.length === 0 ? (
                <Box
                  sx={{
                    height: "100%",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <Typography variant="body2" color="text.secondary">
                    Enroll students to visualize branch distribution.
                  </Typography>
                </Box>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={analyticsData.branchChart}>
                    <CartesianGrid strokeDasharray="3 3" opacity={0.25} />
                    <XAxis dataKey="branch" />
                    <YAxis allowDecimals={false} />
                    <RechartsTooltip />
                    <Bar
                      dataKey="count"
                      name="Enrolled Students"
                      fill="#2563eb"
                      radius={[6, 6, 0, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </Box>
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
              height: 360,
              display: "flex",
              flexDirection: "column",
            }}
          >
            <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
              Enrollment Status Breakdown
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={{ mb: 1 }}>
              Current standing across all registered students
            </Typography>

            <Box sx={{ flex: 1, minHeight: 240 }}>
              {analyticsData.statusChart.length === 0 ? (
                <Box
                  sx={{
                    height: "100%",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <Typography variant="body2" color="text.secondary">
                    No status data available yet.
                  </Typography>
                </Box>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={analyticsData.statusChart}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      innerRadius={55}
                      outerRadius={85}
                      paddingAngle={3}
                    >
                      {analyticsData.statusChart.map((entry, index) => (
                        <Cell
                          key={entry.name}
                          fill={CHART_COLORS[index % CHART_COLORS.length]}
                        />
                      ))}
                    </Pie>
                    <RechartsTooltip />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              )}
            </Box>
          </Paper>
        </Grid>
      </Grid>

      {/* Student Directory Management Section right on Overview for immediate access */}
      {renderStudentsDirectorySection()}
    </Box>
  );

  const renderStudentsDirectorySection = () => (
    <Box>
      <SearchStudent
        searchQuery={searchQuery}
        onSearchChange={handleSearchChange}
        branchFilter={branchFilter}
        onBranchChange={(v) => {
          setBranchFilter(v);
          setPage(0);
        }}
        statusFilter={statusFilter}
        onStatusChange={(v) => {
          setStatusFilter(v);
          setPage(0);
        }}
        semesterFilter={semesterFilter}
        onSemesterChange={(v) => {
          setSemesterFilter(v);
          setPage(0);
        }}
        branches={branches}
        totalCount={students.length}
        filteredCount={filteredStudents.length}
        onResetFilters={handleResetFilters}
        onOpenAddModal={isAdmin ? handleOpenAdd : null}
        onOpenImportModal={isAdmin ? () => setImportOpen(true) : null}
        onExportCsv={canEdit ? () => handleExportCsv(filteredStudents) : null}
        onRefresh={() => loadStudents(false)}
        loading={loading}
      />

      {/* Bulk Action Bar */}
      {selectedIds.length > 0 && (
        <Paper
          elevation={0}
          sx={{
            p: 1.5,
            px: 2.5,
            mb: 2,
            borderRadius: 2.5,
            bgcolor: "primary.main",
            color: "#fff",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: 1.5,
          }}
        >
          <Typography variant="body2" sx={{ fontWeight: 700 }}>
            {selectedIds.length} student record(s) selected
          </Typography>
          <Stack direction="row" spacing={1}>
            <Button
              size="small"
              variant="outlined"
              sx={{
                color: "#fff",
                borderColor: "rgba(255,255,255,0.5)",
                textTransform: "none",
              }}
              onClick={() => {
                const rows = students.filter((s) =>
                  selectedIds.includes(s.reg_no)
                );
                handleExportCsv(rows, "selected_students.csv");
              }}
            >
              Export Selected
            </Button>
            <Button
              size="small"
              variant="contained"
              color="error"
              startIcon={<DeleteSweepRoundedIcon />}
              onClick={handleConfirmBulkDeleteRequest}
              sx={{ textTransform: "none", fontWeight: 700 }}
            >
              Delete Selected
            </Button>
            <Button
              size="small"
              sx={{ color: "#fff", textTransform: "none" }}
              onClick={() => setSelectedIds([])}
            >
              Clear
            </Button>
          </Stack>
        </Paper>
      )}

      <StudentTable
        students={paginatedStudents}
        loading={loading}
        onEdit={canEdit ? handleOpenEdit : null}
        onDelete={isAdmin ? handleConfirmDeleteRequest : null}
        onViewProfile={(s) => setProfileStudent(s)}
        onOpenAdd={isAdmin ? handleOpenAdd : null}
        selectedIds={selectedIds}
        onSelectOne={isAdmin ? handleSelectOne : null}
        onSelectAll={isAdmin ? handleSelectAll : null}
        sortBy={sortBy}
        sortOrder={sortOrder}
        onRequestSort={handleRequestSort}
        page={page}
        rowsPerPage={rowsPerPage}
        totalCount={filteredStudents.length}
        onPageChange={(_, newPage) => setPage(newPage)}
        onRowsPerPageChange={(e) => {
          setRowsPerPage(parseInt(e.target.value, 10));
          setPage(0);
        }}
      />
    </Box>
  );

  const renderLogsSection = () => (
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
          mb: 2,
        }}
      >
        <Box>
          <Typography variant="h6" sx={{ fontWeight: 700 }}>
            Administrative Activity & Audit Trail
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Chronological log of CRUD actions, exports, and bulk operations
          </Typography>
        </Box>
        {logs.length > 0 && (
          <Button
            size="small"
            color="error"
            onClick={() => {
              clearActivityLogs();
              refreshLogs();
              showToast("Activity history cleared", "info");
            }}
            sx={{ textTransform: "none" }}
          >
            Clear History
          </Button>
        )}
      </Box>
      <Divider sx={{ mb: 2 }} />
      {logs.length === 0 ? (
        <Typography variant="body2" color="text.secondary" sx={{ py: 4, textAlign: "center" }}>
          No administrative events logged in this session yet.
        </Typography>
      ) : (
        <Stack spacing={1.5}>
          {logs.map((item) => (
            <Paper
              key={item.id}
              variant="outlined"
              sx={{
                p: 1.75,
                borderRadius: 2,
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                flexWrap: "wrap",
                gap: 1,
              }}
            >
              <Box>
                <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                  {item.action}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {item.details}
                </Typography>
              </Box>
              <Typography variant="caption" color="text.secondary">
                {new Date(item.timestamp).toLocaleString()}
              </Typography>
            </Paper>
          ))}
        </Stack>
      )}
    </Paper>
  );

  const renderSettingsSection = () => (
    <Grid container spacing={3}>
      <Grid size={{ xs: 12, md: 6 }}>
        <Paper
          elevation={0}
          sx={{
            p: 3,
            borderRadius: 3,
            border: "1px solid",
            borderColor: "divider",
          }}
        >
          <Typography variant="h6" sx={{ fontWeight: 700, mb: 0.5 }}>
            Platform Preferences & Connectivity
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Configure appearance and verify backend API status.
          </Typography>

          <Stack spacing={2.5}>
            <Box
              sx={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <Box>
                <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                  Dark Theme Appearance
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Persist dark color palette across browser sessions
                </Typography>
              </Box>
              <FormControlLabel
                control={
                  <Switch
                    checked={Boolean(darkMode)}
                    onChange={onToggleDarkMode}
                  />
                }
                label={darkMode ? "Dark" : "Light"}
              />
            </Box>

            <Divider />

            <Box>
              <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1 }}>
                Change Account Password
              </Typography>
              <Stack spacing={1.5}>
                <TextField
                  size="small"
                  type="password"
                  label="Current Password"
                  value={pwdForm.current_password}
                  onChange={(e) =>
                    setPwdForm((p) => ({
                      ...p,
                      current_password: e.target.value,
                    }))
                  }
                />
                <TextField
                  size="small"
                  type="password"
                  label="New Password (min 8 chars, letters + numbers)"
                  value={pwdForm.new_password}
                  onChange={(e) =>
                    setPwdForm((p) => ({
                      ...p,
                      new_password: e.target.value,
                    }))
                  }
                />
                <Button
                  size="small"
                  variant="contained"
                  sx={{ textTransform: "none", alignSelf: "flex-start" }}
                  onClick={async () => {
                    try {
                      await resetPassword({
                        username: currentUser?.username,
                        current_password: pwdForm.current_password,
                        new_password: pwdForm.new_password,
                      });
                      setPwdForm({ current_password: "", new_password: "" });
                      showToast("Password updated successfully", "success");
                    } catch (err) {
                      showToast(err.message || "Password reset failed", "error");
                    }
                  }}
                >
                  Update Password
                </Button>
              </Stack>
            </Box>

            <Divider />

            <Box>
              <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 0.5 }}>
                Configured REST API Endpoint
              </Typography>
              <Typography
                variant="body2"
                sx={{
                  fontFamily: "monospace",
                  p: 1.25,
                  borderRadius: 1.5,
                  bgcolor: "action.hover",
                  mb: 1.5,
                }}
              >
                {API}
              </Typography>
              <Button
                size="small"
                variant="outlined"
                startIcon={<CheckCircleOutlineRoundedIcon />}
                onClick={async () => {
                  try {
                    await checkHealth();
                    if (onApiStatusChange) onApiStatusChange(true);
                    showToast("Backend API is healthy and reachable", "success");
                  } catch {
                    if (onApiStatusChange) onApiStatusChange(false);
                    showToast("Backend health check failed", "error");
                  }
                }}
                sx={{ textTransform: "none" }}
              >
                Test API Health
              </Button>
            </Box>
          </Stack>
        </Paper>
      </Grid>

      {isAdmin && (
        <Grid size={{ xs: 12, md: 6 }}>
          <Paper
            elevation={0}
            sx={{
              p: 3,
              borderRadius: 3,
              border: "1px solid",
              borderColor: "divider",
            }}
          >
            <Typography variant="h6" sx={{ fontWeight: 700, mb: 0.5 }}>
              RBAC User Provisioning (Admin Only)
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2.5 }}>
              Create new Admin, Faculty (branch-scoped), or Student (record-scoped) accounts.
            </Typography>

            <Stack spacing={1.5}>
              <TextField
                size="small"
                label="Username"
                value={newUserForm.username}
                onChange={(e) =>
                  setNewUserForm((p) => ({ ...p, username: e.target.value }))
                }
              />
              <TextField
                size="small"
                label="Full Name"
                value={newUserForm.full_name}
                onChange={(e) =>
                  setNewUserForm((p) => ({ ...p, full_name: e.target.value }))
                }
              />
              <TextField
                size="small"
                type="password"
                label="Initial Password"
                value={newUserForm.password}
                onChange={(e) =>
                  setNewUserForm((p) => ({ ...p, password: e.target.value }))
                }
              />
              <TextField
                size="small"
                label="Role (Admin, Faculty, Student)"
                value={newUserForm.role}
                onChange={(e) =>
                  setNewUserForm((p) => ({ ...p, role: e.target.value }))
                }
              />
              {newUserForm.role === "Faculty" && (
                <TextField
                  size="small"
                  label="Assigned Branches (comma-separated, e.g. CSE,ECE)"
                  value={newUserForm.assigned_branches}
                  onChange={(e) =>
                    setNewUserForm((p) => ({
                      ...p,
                      assigned_branches: e.target.value,
                    }))
                  }
                />
              )}
              {newUserForm.role === "Student" && (
                <TextField
                  size="small"
                  label="Linked Registration No (e.g. REG2026001)"
                  value={newUserForm.linked_reg_no}
                  onChange={(e) =>
                    setNewUserForm((p) => ({
                      ...p,
                      linked_reg_no: e.target.value,
                    }))
                  }
                />
              )}
              <Button
                variant="contained"
                size="small"
                sx={{ textTransform: "none", alignSelf: "flex-start" }}
                onClick={async () => {
                  try {
                    await createPlatformUser({
                      username: newUserForm.username,
                      password: newUserForm.password,
                      role: newUserForm.role,
                      full_name: newUserForm.full_name,
                      assigned_branches: String(
                        newUserForm.assigned_branches || ""
                      )
                        .split(",")
                        .map((b) => b.trim())
                        .filter(Boolean),
                      linked_reg_no: newUserForm.linked_reg_no,
                    });
                    showToast(
                      `Created ${newUserForm.role} user '${newUserForm.username}'`,
                      "success"
                    );
                    setNewUserForm({
                      username: "",
                      password: "",
                      role: "Student",
                      full_name: "",
                      assigned_branches: "CSE",
                      linked_reg_no: "",
                    });
                    refreshLogs();
                  } catch (err) {
                    showToast(err.message || "Failed to create user", "error");
                  }
                }}
              >
                Create User Account
              </Button>
            </Stack>
          </Paper>
        </Grid>
      )}
    </Grid>
  );

  // Page header title and subtitle mapping
  const headerMeta = {
    "/": {
      title: "Student Management System",
      subtitle:
        "Enterprise overview of student enrollment, department analytics, and directory operations.",
    },
    "/students": {
      title: "Student Directory",
      subtitle:
        "Search, filter, enroll, update, and bulk-manage student records.",
    },
    "/academics": {
      title: "Academic Courses & Enrollments",
      subtitle:
        "Manage curriculum courses, faculty assignments, capacity limits, and student course enrollments.",
    },
    "/attendance": {
      title: "Attendance Management & Reports",
      subtitle:
        "Record classroom session attendance (Present, Absent, Late, Excused) and monitor course-wise and student-wise compliance.",
    },
    "/performance": {
      title: "Grades, Assessments & CGPA",
      subtitle:
        "Record assessment marks, configure grading scales, and compute credit-weighted GPA and CGPA.",
    },
    "/analytics": {
      title: "Advanced Institutional Analytics & AI Assistant",
      subtitle:
        "Multi-dimensional enrollment, attendance trends, grade distributions, and grounded AI analytics.",
    },
    "/reports": {
      title: "Reports, Live Preview & Multi-Format Exports",
      subtitle:
        "Generate, preview, and download RBAC-enforced PDF, Excel (.xlsx), and CSV reports with AI narratives.",
    },
    "/logs": {
      title: "Activity & Audit Logs",
      subtitle: "Review administrative operations performed in the portal.",
    },
    "/settings": {
      title: "System Settings",
      subtitle: "Manage theme mode and verify backend API connectivity.",
    },
  }[activePath] || {
    title: "Student Management System",
    subtitle: "Manage and analyze student records.",
  };

  return (
    <Box className="dashboard-container">
      {/* Top Page Header Banner */}
      <Box
        sx={{
          display: "flex",
          flexDirection: { xs: "column", md: "row" },
          alignItems: { xs: "flex-start", md: "center" },
          justifyContent: "space-between",
          gap: 2,
          mb: 3,
        }}
      >
        <Box>
          <Typography
            variant="h4"
            component="h1"
            sx={{ fontWeight: 800, letterSpacing: -0.5 }}
          >
            {headerMeta.title}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            {headerMeta.subtitle}
          </Typography>
        </Box>

        <Stack direction="row" spacing={1.25} flexWrap="wrap" useFlexGap>
          <Button
            variant="outlined"
            size="small"
            startIcon={<RefreshRoundedIcon />}
            onClick={() => loadStudents(false)}
            sx={{ textTransform: "none", fontWeight: 600, borderRadius: 2 }}
          >
            Refresh Students
          </Button>
          {isAdmin && (
            <Button
              variant="outlined"
              size="small"
              startIcon={<FileUploadRoundedIcon />}
              onClick={() => setImportOpen(true)}
              sx={{ textTransform: "none", fontWeight: 600, borderRadius: 2 }}
            >
              Import CSV
            </Button>
          )}
          {isAdmin && (
            <Button
              variant="contained"
              size="small"
              startIcon={<PersonAddAlt1RoundedIcon />}
              onClick={handleOpenAdd}
              sx={{
                textTransform: "none",
                fontWeight: 600,
                borderRadius: 2,
                px: 2,
              }}
            >
              Add Student
            </Button>
          )}
        </Stack>
      </Box>

      {/* Active Route Content */}
      {activePath === "/students" && renderStudentsDirectorySection()}
      {activePath === "/academics" && (
        <AcademicsWorkspace
          students={students}
          currentUser={currentUser}
          onNotify={showToast}
          onSelectBranchRoster={(b) => {
            setBranchFilter(b);
            navigate("/students");
          }}
        />
      )}
      {activePath === "/attendance" && (
        <AttendanceWorkspace
          students={students}
          currentUser={currentUser}
          onNotify={showToast}
          onRefreshStudents={loadStudents}
        />
      )}
      {activePath === "/performance" && (
        <PerformanceWorkspace
          students={students}
          currentUser={currentUser}
          onNotify={showToast}
          onRefreshStudents={loadStudents}
        />
      )}
      {activePath === "/analytics" && (
        <AdvancedAnalyticsWorkspace
          students={students}
          currentUser={currentUser}
          onNotify={showToast}
        />
      )}
      {activePath === "/reports" && (
        <ReportsAndExportsWorkspace
          students={students}
          currentUser={currentUser}
          onNotify={showToast}
        />
      )}
      {activePath === "/logs" && renderLogsSection()}
      {activePath === "/settings" && renderSettingsSection()}
      {(activePath === "/" ||
        ![
          "/students",
          "/academics",
          "/attendance",
          "/performance",
          "/analytics",
          "/reports",
          "/logs",
          "/settings",
        ].includes(activePath)) &&
        renderOverviewSection()}

      {/* Add / Edit Student Modal */}
      <StudentForm
        open={formOpen}
        onClose={() => {
          setFormOpen(false);
          setEditingStudent(null);
        }}
        onSubmit={handleFormSubmit}
        initialData={editingStudent}
        submitting={submitting}
        existingBranches={branches}
      />

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={deleteDialog.open}
        onClose={
          submitting
            ? undefined
            : () =>
                setDeleteDialog({
                  open: false,
                  mode: "single",
                  targetRegNo: null,
                  targetName: "",
                })
        }
        maxWidth="xs"
        fullWidth
        PaperProps={{ sx: { borderRadius: 3 } }}
      >
        <DialogTitle sx={{ fontWeight: 700 }}>
          Confirm Student Deletion
        </DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary">
            Are you sure you want to permanently delete{" "}
            <strong>{deleteDialog.targetName}</strong> from the database? This
            action cannot be undone.
          </Typography>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button
            onClick={() =>
              setDeleteDialog({
                open: false,
                mode: "single",
                targetRegNo: null,
                targetName: "",
              })
            }
            disabled={submitting}
            color="inherit"
            sx={{ textTransform: "none" }}
          >
            Cancel
          </Button>
          <Button
            onClick={handleExecuteDelete}
            color="error"
            variant="contained"
            disabled={submitting}
            sx={{ textTransform: "none", fontWeight: 600, borderRadius: 2 }}
          >
            {submitting ? "Deleting..." : "Delete Record"}
          </Button>
        </DialogActions>
      </Dialog>

      {/* CSV Import Modal */}
      <Dialog
        open={importOpen}
        onClose={submitting ? undefined : () => setImportOpen(false)}
        maxWidth="md"
        fullWidth
        PaperProps={{ sx: { borderRadius: 3 } }}
      >
        <DialogTitle
          sx={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <Typography variant="h6" sx={{ fontWeight: 700 }}>
            Bulk Import Students via CSV
          </Typography>
          <IconButton onClick={() => setImportOpen(false)} disabled={submitting}>
            <CloseRoundedIcon />
          </IconButton>
        </DialogTitle>
        <Divider />
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Upload a `.csv` file or paste CSV lines with headers:{" "}
            <code>reg_no,roll_no,name,age,branch,email,semester,status</code>
          </Typography>

          <Button
            variant="outlined"
            component="label"
            size="small"
            sx={{ mb: 2, textTransform: "none", borderRadius: 2 }}
          >
            Choose CSV File
            <input
              type="file"
              accept=".csv,text/csv"
              hidden
              onChange={handleCsvFileSelect}
            />
          </Button>

          <TextField
            label="Or Paste CSV Content"
            multiline
            rows={5}
            fullWidth
            placeholder={
              "reg_no,roll_no,name,age,branch\nREG2026101,101,Aarav Sharma,20,CSE"
            }
            value={csvText}
            onChange={(e) => {
              setCsvText(e.target.value);
              setCsvPreview(parseCsvText(e.target.value));
            }}
            sx={{ mb: 2 }}
          />

          <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
            Preview: {csvPreview.length} valid row(s) detected
          </Typography>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button
            onClick={() => setImportOpen(false)}
            disabled={submitting}
            color="inherit"
            sx={{ textTransform: "none" }}
          >
            Cancel
          </Button>
          <Button
            variant="contained"
            onClick={handleExecuteImport}
            disabled={submitting || csvPreview.length === 0}
            sx={{ textTransform: "none", fontWeight: 600, borderRadius: 2 }}
          >
            {submitting
              ? "Importing..."
              : `Import ${csvPreview.length} Student(s)`}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Detailed Student Profile Drawer */}
      <Drawer
        anchor="right"
        open={Boolean(profileStudent)}
        onClose={() => setProfileStudent(null)}
        PaperProps={{
          sx: { width: { xs: "100%", sm: 400 }, p: 3 },
        }}
      >
        {profileStudent && (
          <Box>
            <Box
              sx={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                mb: 2,
              }}
            >
              <Typography variant="h6" sx={{ fontWeight: 700 }}>
                Student Profile
              </Typography>
              <IconButton onClick={() => setProfileStudent(null)}>
                <CloseRoundedIcon />
              </IconButton>
            </Box>
            <Divider sx={{ mb: 3 }} />

            <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 3 }}>
              <Avatar
                sx={{
                  width: 60,
                  height: 60,
                  bgcolor: "primary.main",
                  fontSize: "1.35rem",
                  fontWeight: 800,
                }}
              >
                {String(profileStudent.name || "ST")
                  .slice(0, 2)
                  .toUpperCase()}
              </Avatar>
              <Box>
                <Typography variant="h6" sx={{ fontWeight: 800 }}>
                  {profileStudent.name}
                </Typography>
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{ fontFamily: "monospace" }}
                >
                  Reg No: {profileStudent.reg_no}
                </Typography>
                <Chip
                  size="small"
                  label={profileStudent.status || "Active"}
                  color="success"
                  sx={{ mt: 0.5, fontWeight: 600 }}
                />
              </Box>
            </Box>

            <Stack spacing={1.5} sx={{ mb: 3 }}>
              {[
                { label: "Roll Number", value: profileStudent.roll_no },
                { label: "Department / Branch", value: profileStudent.branch },
                { label: "Age", value: `${profileStudent.age} years` },
                {
                  label: "Semester",
                  value: profileStudent.semester
                    ? `Semester ${profileStudent.semester}`
                    : "Standard",
                },
                {
                  label: "Academic Year",
                  value: profileStudent.academic_year || "2025-2026",
                },
                {
                  label: "Email",
                  value: profileStudent.email || "Not provided",
                },
                {
                  label: "Phone",
                  value: profileStudent.phone || "Not provided",
                },
                {
                  label: "CGPA",
                  value:
                    profileStudent.gpa !== null &&
                    profileStudent.gpa !== undefined
                      ? `${Number(profileStudent.gpa).toFixed(2)} / 10.0`
                      : "Not assessed",
                },
                {
                  label: "Attendance",
                  value:
                    profileStudent.attendance_pct !== null &&
                    profileStudent.attendance_pct !== undefined
                      ? `${profileStudent.attendance_pct}%`
                      : "Not recorded",
                },
              ].map((field) => (
                <Box
                  key={field.label}
                  sx={{
                    display: "flex",
                    justifyContent: "space-between",
                    py: 1,
                    borderBottom: "1px dashed",
                    borderColor: "divider",
                  }}
                >
                  <Typography variant="body2" color="text.secondary">
                    {field.label}
                  </Typography>
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>
                    {field.value}
                  </Typography>
                </Box>
              ))}
            </Stack>

            <Stack direction="row" spacing={1.5}>
              <Button
                variant="contained"
                fullWidth
                startIcon={<EditRoundedIcon />}
                onClick={() => {
                  const target = profileStudent;
                  setProfileStudent(null);
                  handleOpenEdit(target);
                }}
                sx={{ textTransform: "none", borderRadius: 2 }}
              >
                Edit Profile
              </Button>
              <Button
                variant="outlined"
                color="error"
                fullWidth
                onClick={() =>
                  handleConfirmDeleteRequest(
                    profileStudent.reg_no,
                    profileStudent
                  )
                }
                sx={{ textTransform: "none", borderRadius: 2 }}
              >
                Delete
              </Button>
            </Stack>
          </Box>
        )}
      </Drawer>

      {/* Non-blocking Toast Notification */}
      <Snackbar
        open={toast.open}
        autoHideDuration={4000}
        onClose={() => setToast((prev) => ({ ...prev, open: false }))}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
      >
        <Alert
          onClose={() => setToast((prev) => ({ ...prev, open: false }))}
          severity={toast.severity}
          variant="filled"
          sx={{ width: "100%", borderRadius: 2 }}
        >
          {toast.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}
