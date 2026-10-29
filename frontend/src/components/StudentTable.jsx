import React from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TableSortLabel,
  TablePagination,
  Paper,
  Checkbox,
  IconButton,
  Tooltip,
  Chip,
  Box,
  Typography,
  Button,
  Avatar,
  Skeleton,
  LinearProgress,
  Stack,
  useMediaQuery,
  useTheme,
} from "@mui/material";
import EditRoundedIcon from "@mui/icons-material/EditRounded";
import DeleteOutlineRoundedIcon from "@mui/icons-material/DeleteOutlineRounded";
import VisibilityRoundedIcon from "@mui/icons-material/VisibilityRounded";
import SchoolRoundedIcon from "@mui/icons-material/SchoolRounded";
import PersonAddAlt1RoundedIcon from "@mui/icons-material/PersonAddAlt1Rounded";

const STATUS_COLOR_MAP = {
  Active: "success",
  "On Leave": "warning",
  Probation: "error",
  Graduated: "info",
  Inactive: "default",
};

const getInitials = (name = "") => {
  const parts = String(name).trim().split(/\s+/);
  if (parts.length === 0 || !parts[0]) return "ST";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
};

export default function StudentTable({
  students = [],
  onDelete,
  onEdit,
  onViewProfile,
  onOpenAdd,
  loading = false,
  selectedIds = [],
  onSelectOne,
  onSelectAll,
  sortBy = "reg_no",
  sortOrder = "asc",
  onRequestSort,
  page = 0,
  rowsPerPage = 10,
  totalCount,
  onPageChange,
  onRowsPerPageChange,
}) {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("md"));

  const safeStudents = Array.isArray(students) ? students : [];
  const count = totalCount !== undefined ? totalCount : safeStudents.length;

  const allSelected =
    safeStudents.length > 0 &&
    safeStudents.every((s) => selectedIds.includes(s.reg_no));
  const someSelected =
    safeStudents.some((s) => selectedIds.includes(s.reg_no)) && !allSelected;

  const createSortHandler = (property) => () => {
    if (onRequestSort) {
      onRequestSort(property);
    }
  };

  if (loading) {
    return (
      <Paper
        elevation={0}
        sx={{
          p: 2.5,
          borderRadius: 3,
          border: "1px solid",
          borderColor: "divider",
        }}
      >
        {[1, 2, 3, 4, 5].map((row) => (
          <Box
            key={row}
            sx={{
              display: "flex",
              alignItems: "center",
              gap: 2,
              py: 1.5,
              borderBottom: row < 5 ? "1px solid" : "none",
              borderColor: "divider",
            }}
          >
            <Skeleton variant="circular" width={36} height={36} />
            <Skeleton variant="text" width="18%" height={28} />
            <Skeleton variant="text" width="15%" height={28} />
            <Skeleton variant="text" width="25%" height={28} />
            <Skeleton variant="text" width="15%" height={28} />
            <Skeleton variant="rectangular" width={90} height={28} sx={{ borderRadius: 1 }} />
          </Box>
        ))}
      </Paper>
    );
  }

  if (safeStudents.length === 0) {
    return (
      <Paper
        elevation={0}
        sx={{
          p: 6,
          textAlign: "center",
          borderRadius: 3,
          border: "1px dashed",
          borderColor: "divider",
        }}
      >
        <Box
          sx={{
            width: 64,
            height: 64,
            borderRadius: "50%",
            bgcolor: "action.hover",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            mx: "auto",
            mb: 2,
            color: "primary.main",
          }}
        >
          <SchoolRoundedIcon fontSize="large" />
        </Box>
        <Typography variant="h6" sx={{ fontWeight: 700, mb: 0.5 }}>
          No Student Records Found
        </Typography>
        <Typography
          variant="body2"
          color="text.secondary"
          sx={{ maxWidth: 420, mx: "auto", mb: 3 }}
        >
          No records match your current search or filter criteria, or the
          database collection is currently empty.
        </Typography>
        {onOpenAdd && (
          <Button
            variant="contained"
            startIcon={<PersonAddAlt1RoundedIcon />}
            onClick={onOpenAdd}
            sx={{ textTransform: "none", fontWeight: 600, borderRadius: 2 }}
          >
            Enroll First Student
          </Button>
        )}
      </Paper>
    );
  }

  return (
    <Paper
      elevation={0}
      sx={{
        borderRadius: 3,
        border: "1px solid",
        borderColor: "divider",
        overflow: "hidden",
      }}
    >
      {!isMobile ? (
        <Box sx={{ overflowX: "auto" }}>
          <Table size="medium" aria-label="Student directory table">
            <TableHead>
              <TableRow
                sx={{
                  bgcolor:
                    theme.palette.mode === "dark"
                      ? "rgba(255,255,255,0.03)"
                      : "rgba(241, 245, 249, 0.8)",
                }}
              >
                {onSelectAll && (
                  <TableCell padding="checkbox">
                    <Checkbox
                      color="primary"
                      indeterminate={someSelected}
                      checked={allSelected}
                      onChange={(e) =>
                        onSelectAll(
                          e.target.checked
                            ? safeStudents.map((s) => s.reg_no)
                            : []
                        )
                      }
                      inputProps={{ "aria-label": "Select all students" }}
                    />
                  </TableCell>
                )}

                <TableCell sx={{ fontWeight: 700 }}>
                  <TableSortLabel
                    active={sortBy === "name"}
                    direction={sortBy === "name" ? sortOrder : "asc"}
                    onClick={createSortHandler("name")}
                  >
                    Student
                  </TableSortLabel>
                </TableCell>

                <TableCell sx={{ fontWeight: 700 }}>
                  <TableSortLabel
                    active={sortBy === "reg_no"}
                    direction={sortBy === "reg_no" ? sortOrder : "asc"}
                    onClick={createSortHandler("reg_no")}
                  >
                    Reg No
                  </TableSortLabel>
                </TableCell>

                <TableCell sx={{ fontWeight: 700 }}>
                  <TableSortLabel
                    active={sortBy === "roll_no"}
                    direction={sortBy === "roll_no" ? sortOrder : "asc"}
                    onClick={createSortHandler("roll_no")}
                  >
                    Roll No
                  </TableSortLabel>
                </TableCell>

                <TableCell sx={{ fontWeight: 700 }}>
                  <TableSortLabel
                    active={sortBy === "branch"}
                    direction={sortBy === "branch" ? sortOrder : "asc"}
                    onClick={createSortHandler("branch")}
                  >
                    Branch
                  </TableSortLabel>
                </TableCell>

                <TableCell sx={{ fontWeight: 700 }}>
                  <TableSortLabel
                    active={sortBy === "age"}
                    direction={sortBy === "age" ? sortOrder : "asc"}
                    onClick={createSortHandler("age")}
                  >
                    Age
                  </TableSortLabel>
                </TableCell>

                <TableCell sx={{ fontWeight: 700 }}>Status</TableCell>

                <TableCell sx={{ fontWeight: 700 }}>Academic Metrics</TableCell>

                <TableCell align="right" sx={{ fontWeight: 700 }}>
                  Actions
                </TableCell>
              </TableRow>
            </TableHead>

            <TableBody>
              {safeStudents.map((s) => {
                const isSelected = selectedIds.includes(s.reg_no);
                const statusLabel = s.status || "Active";

                return (
                  <TableRow
                    key={s.reg_no}
                    hover
                    selected={isSelected}
                    sx={{
                      "&:last-child td": { borderBottom: 0 },
                      cursor: onViewProfile ? "pointer" : "default",
                    }}
                    onClick={() => onViewProfile && onViewProfile(s)}
                  >
                    {onSelectOne && (
                      <TableCell
                        padding="checkbox"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <Checkbox
                          color="primary"
                          checked={isSelected}
                          onChange={() => onSelectOne(s.reg_no)}
                          inputProps={{
                            "aria-label": `Select ${s.name}`,
                          }}
                        />
                      </TableCell>
                    )}

                    <TableCell>
                      <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
                        <Avatar
                          sx={{
                            width: 36,
                            height: 36,
                            fontSize: "0.85rem",
                            fontWeight: 700,
                            bgcolor: "primary.main",
                            color: "#fff",
                          }}
                        >
                          {getInitials(s.name)}
                        </Avatar>
                        <Box>
                          <Typography
                            variant="body2"
                            sx={{ fontWeight: 600, color: "text.primary" }}
                          >
                            {s.name}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {s.email ||
                              (s.semester
                                ? `Semester ${s.semester}`
                                : "Registered Student")}
                          </Typography>
                        </Box>
                      </Box>
                    </TableCell>

                    <TableCell>
                      <Typography
                        variant="body2"
                        sx={{
                          fontFamily: "monospace",
                          fontWeight: 600,
                        }}
                      >
                        {s.reg_no}
                      </Typography>
                    </TableCell>

                    <TableCell>{s.roll_no}</TableCell>

                    <TableCell>
                      <Chip
                        label={s.branch}
                        size="small"
                        variant="outlined"
                        color="primary"
                        sx={{ fontWeight: 600 }}
                      />
                    </TableCell>

                    <TableCell>{s.age}</TableCell>

                    <TableCell>
                      <Chip
                        label={statusLabel}
                        size="small"
                        color={STATUS_COLOR_MAP[statusLabel] || "default"}
                        sx={{ fontWeight: 600, fontSize: "0.72rem" }}
                      />
                    </TableCell>

                    <TableCell sx={{ minWidth: 150 }}>
                      {s.gpa !== null && s.gpa !== undefined ? (
                        <Box>
                          <Typography variant="caption" sx={{ fontWeight: 600 }}>
                            GPA: {Number(s.gpa).toFixed(2)}
                            {s.attendance_pct !== null &&
                            s.attendance_pct !== undefined
                              ? ` • Att: ${s.attendance_pct}%`
                              : ""}
                          </Typography>
                          <LinearProgress
                            variant="determinate"
                            value={Math.min(
                              100,
                              s.attendance_pct !== null &&
                                s.attendance_pct !== undefined
                                ? Number(s.attendance_pct)
                                : Number(s.gpa) * 10
                            )}
                            sx={{ height: 5, borderRadius: 2, mt: 0.5 }}
                          />
                        </Box>
                      ) : s.attendance_pct !== null &&
                        s.attendance_pct !== undefined ? (
                        <Box>
                          <Typography variant="caption" sx={{ fontWeight: 600 }}>
                            Attendance: {s.attendance_pct}%
                          </Typography>
                          <LinearProgress
                            variant="determinate"
                            value={Math.min(100, Number(s.attendance_pct))}
                            sx={{ height: 5, borderRadius: 2, mt: 0.5 }}
                          />
                        </Box>
                      ) : (
                        <Typography variant="caption" color="text.secondary">
                          Standard Track
                        </Typography>
                      )}
                    </TableCell>

                    <TableCell
                      align="right"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <Stack
                        direction="row"
                        spacing={0.5}
                        justifyContent="flex-end"
                      >
                        {onViewProfile && (
                          <Tooltip title="View Student Profile">
                            <IconButton
                              size="small"
                              onClick={() => onViewProfile(s)}
                              aria-label={`View ${s.name}`}
                            >
                              <VisibilityRoundedIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        )}
                        {onEdit && (
                          <Tooltip title="Edit Student">
                            <IconButton
                              size="small"
                              color="primary"
                              onClick={() => onEdit(s)}
                              aria-label={`Edit ${s.name}`}
                            >
                              <EditRoundedIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        )}
                        {onDelete && (
                          <Tooltip title="Delete Student">
                            <IconButton
                              size="small"
                              color="error"
                              onClick={() => onDelete(s.reg_no, s)}
                              aria-label={`Delete ${s.name}`}
                            >
                              <DeleteOutlineRoundedIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        )}
                      </Stack>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </Box>
      ) : (
        /* Responsive Mobile Card View */
        <Box sx={{ p: 2, display: "flex", flexDirection: "column", gap: 2 }}>
          {safeStudents.map((s) => {
            const statusLabel = s.status || "Active";
            return (
              <Paper
                key={s.reg_no}
                variant="outlined"
                sx={{ p: 2, borderRadius: 2.5 }}
              >
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    mb: 1.5,
                  }}
                >
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
                    <Avatar
                      sx={{
                        width: 40,
                        height: 40,
                        bgcolor: "primary.main",
                        fontWeight: 700,
                      }}
                    >
                      {getInitials(s.name)}
                    </Avatar>
                    <Box>
                      <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
                        {s.name}
                      </Typography>
                      <Typography
                        variant="caption"
                        color="text.secondary"
                        sx={{ fontFamily: "monospace" }}
                      >
                        Reg: {s.reg_no} • Roll: {s.roll_no}
                      </Typography>
                    </Box>
                  </Box>
                  <Chip
                    label={statusLabel}
                    size="small"
                    color={STATUS_COLOR_MAP[statusLabel] || "default"}
                  />
                </Box>

                <Stack direction="row" spacing={1} sx={{ mb: 2 }} flexWrap="wrap">
                  <Chip label={`Branch: ${s.branch}`} size="small" variant="outlined" />
                  <Chip label={`Age: ${s.age}`} size="small" variant="outlined" />
                  {s.semester && (
                    <Chip label={`Sem ${s.semester}`} size="small" variant="outlined" />
                  )}
                </Stack>

                <Stack direction="row" spacing={1}>
                  {onViewProfile && (
                    <Button
                      size="small"
                      variant="outlined"
                      fullWidth
                      onClick={() => onViewProfile(s)}
                    >
                      Profile
                    </Button>
                  )}
                  {onEdit && (
                    <Button
                      size="small"
                      variant="contained"
                      fullWidth
                      onClick={() => onEdit(s)}
                    >
                      Edit
                    </Button>
                  )}
                  {onDelete && (
                    <Button
                      size="small"
                      variant="outlined"
                      color="error"
                      fullWidth
                      onClick={() => onDelete(s.reg_no, s)}
                    >
                      Delete
                    </Button>
                  )}
                </Stack>
              </Paper>
            );
          })}
        </Box>
      )}

      {onPageChange && (
        <TablePagination
          component="div"
          count={count}
          page={page}
          onPageChange={onPageChange}
          rowsPerPage={rowsPerPage}
          onRowsPerPageChange={onRowsPerPageChange}
          rowsPerPageOptions={[5, 10, 25, 50]}
        />
      )}
    </Paper>
  );
}
