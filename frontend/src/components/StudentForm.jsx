import React, { useState, useEffect } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  Grid,
  MenuItem,
  Typography,
  Box,
  IconButton,
  Divider,
  Alert,
} from "@mui/material";
import CloseRoundedIcon from "@mui/icons-material/CloseRounded";

const DEFAULT_BRANCHES = [
  "CSE",
  "ECE",
  "EEE",
  "MECH",
  "CIVIL",
  "IT",
  "AI & DS",
  "CSBS",
  "BIOTECH",
];

const STATUS_CHOICES = [
  "Active",
  "On Leave",
  "Probation",
  "Graduated",
  "Inactive",
];

const SEMESTER_CHOICES = ["1", "2", "3", "4", "5", "6", "7", "8"];

const INITIAL_FORM = {
  reg_no: "",
  roll_no: "",
  name: "",
  age: "",
  branch: "",
  email: "",
  phone: "",
  semester: "1",
  academic_year: "2025-2026",
  admission_date: "",
  status: "Active",
  gpa: "",
  attendance_pct: "",
};

export default function StudentForm({
  open = false,
  onClose,
  onSubmit,
  initialData = null,
  submitting = false,
  existingBranches = [],
}) {
  const isEdit = Boolean(initialData && initialData.reg_no);
  const [form, setForm] = useState(INITIAL_FORM);
  const [errors, setErrors] = useState({});
  const [submitError, setSubmitError] = useState("");

  const branchOptions = Array.from(
    new Set([...DEFAULT_BRANCHES, ...existingBranches].filter(Boolean))
  );

  useEffect(() => {
    if (initialData) {
      setForm({
        reg_no: initialData.reg_no ?? "",
        roll_no: initialData.roll_no ?? "",
        name: initialData.name ?? "",
        age: initialData.age ?? "",
        branch: initialData.branch ?? "",
        email: initialData.email ?? "",
        phone: initialData.phone ?? "",
        semester: initialData.semester || "1",
        academic_year: initialData.academic_year || "2025-2026",
        admission_date: initialData.admission_date || "",
        status: initialData.status || "Active",
        gpa:
          initialData.gpa !== null && initialData.gpa !== undefined
            ? String(initialData.gpa)
            : "",
        attendance_pct:
          initialData.attendance_pct !== null &&
          initialData.attendance_pct !== undefined
            ? String(initialData.attendance_pct)
            : "",
      });
    } else {
      setForm(INITIAL_FORM);
    }
    setErrors({});
    setSubmitError("");
  }, [initialData, open]);

  const validate = () => {
    const nextErrors = {};
    const regNo = String(form.reg_no || "").trim();
    const rollNo = String(form.roll_no || "").trim();
    const name = String(form.name || "").trim();
    const branch = String(form.branch || "").trim();
    const ageNum = Number(form.age);

    if (!regNo) {
      nextErrors.reg_no = "Registration number is required";
    } else if (!/^[A-Za-z0-9]+$/.test(regNo)) {
      nextErrors.reg_no = "Must be alphanumeric (letters and digits only)";
    }

    if (!rollNo) {
      nextErrors.roll_no = "Roll number is required";
    }

    if (!name) {
      nextErrors.name = "Student name is required";
    } else if (name.length < 2) {
      nextErrors.name = "Name must be at least 2 characters";
    }

    if (form.age === "" || form.age === null || Number.isNaN(ageNum)) {
      nextErrors.age = "Valid age is required";
    } else if (!Number.isInteger(ageNum) || ageNum <= 0 || ageNum > 100) {
      nextErrors.age = "Age must be a whole number between 1 and 100";
    }

    if (!branch) {
      nextErrors.branch = "Branch / Department is required";
    }

    if (form.email && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(form.email.trim())) {
      nextErrors.email = "Enter a valid email address";
    }

    if (form.gpa !== "") {
      const g = Number(form.gpa);
      if (Number.isNaN(g) || g < 0 || g > 10) {
        nextErrors.gpa = "GPA must be between 0.0 and 10.0";
      }
    }

    if (form.attendance_pct !== "") {
      const att = Number(form.attendance_pct);
      if (Number.isNaN(att) || att < 0 || att > 100) {
        nextErrors.attendance_pct = "Attendance must be between 0% and 100%";
      }
    }

    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  };

  const handleFieldChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
    if (errors[name]) {
      setErrors((prev) => ({ ...prev, [name]: undefined }));
    }
    if (submitError) {
      setSubmitError("");
    }
  };

  const handleFormSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) return;

    try {
      await onSubmit({
        ...form,
        reg_no: String(form.reg_no).trim(),
        roll_no: String(form.roll_no).trim(),
        name: String(form.name).trim(),
        age: Number(form.age),
        branch: String(form.branch).trim(),
      });
    } catch (err) {
      setSubmitError(err?.message || "Failed to save student record");
    }
  };

  return (
    <Dialog
      open={open}
      onClose={submitting ? undefined : onClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: { borderRadius: 3 },
      }}
    >
      <DialogTitle
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          pb: 1.5,
        }}
      >
        <Box>
          <Typography variant="h6" sx={{ fontWeight: 700 }}>
            {isEdit ? "Edit Student Record" : "Enroll New Student"}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {isEdit
              ? `Updating academic record for Registration No: ${form.reg_no}`
              : "Enter core registration details and optional academic metadata."}
          </Typography>
        </Box>
        <IconButton
          onClick={onClose}
          disabled={submitting}
          aria-label="Close modal"
        >
          <CloseRoundedIcon />
        </IconButton>
      </DialogTitle>

      <Divider />

      <form onSubmit={handleFormSubmit} noValidate>
        <DialogContent sx={{ pt: 2.5 }}>
          {submitError && (
            <Alert severity="error" sx={{ mb: 2, borderRadius: 2 }}>
              {submitError}
            </Alert>
          )}

          <Typography
            variant="overline"
            color="primary"
            sx={{ fontWeight: 700, display: "block", mb: 1.5 }}
          >
            Core Registration Details (Required)
          </Typography>

          <Grid container spacing={2}>
            <Grid size={{ xs: 12, sm: 6 }}>
              <TextField
                label="Registration Number *"
                name="reg_no"
                fullWidth
                size="small"
                value={form.reg_no}
                onChange={handleFieldChange}
                disabled={isEdit || submitting}
                error={Boolean(errors.reg_no)}
                helperText={
                  errors.reg_no ||
                  (isEdit
                    ? "Primary identifier (cannot be changed)"
                    : "Alphanumeric ID, e.g., REG2026001")
                }
              />
            </Grid>

            <Grid size={{ xs: 12, sm: 6 }}>
              <TextField
                label="Roll Number *"
                name="roll_no"
                fullWidth
                size="small"
                value={form.roll_no}
                onChange={handleFieldChange}
                disabled={submitting}
                error={Boolean(errors.roll_no)}
                helperText={errors.roll_no || "Class or university roll number"}
              />
            </Grid>

            <Grid size={{ xs: 12, sm: 6 }}>
              <TextField
                label="Full Name *"
                name="name"
                fullWidth
                size="small"
                value={form.name}
                onChange={handleFieldChange}
                disabled={submitting}
                error={Boolean(errors.name)}
                helperText={errors.name}
              />
            </Grid>

            <Grid size={{ xs: 12, sm: 3 }}>
              <TextField
                label="Age *"
                name="age"
                type="number"
                fullWidth
                size="small"
                value={form.age}
                onChange={handleFieldChange}
                disabled={submitting}
                error={Boolean(errors.age)}
                helperText={errors.age}
              />
            </Grid>

            <Grid size={{ xs: 12, sm: 3 }}>
              <TextField
                label="Branch / Dept *"
                name="branch"
                fullWidth
                size="small"
                value={form.branch}
                onChange={handleFieldChange}
                disabled={submitting}
                error={Boolean(errors.branch)}
                helperText={errors.branch || "e.g., CSE, ECE, MECH"}
                placeholder="CSE"
                slotProps={{
                  htmlInput: { list: "branch-suggestions" },
                }}
              />
              <datalist id="branch-suggestions">
                {branchOptions.map((b) => (
                  <option key={b} value={b} />
                ))}
              </datalist>
            </Grid>
          </Grid>

          <Divider sx={{ my: 2.5 }} />

          <Typography
            variant="overline"
            color="text.secondary"
            sx={{ fontWeight: 700, display: "block", mb: 1.5 }}
          >
            Extended Academic & Contact Profile (Optional)
          </Typography>

          <Grid container spacing={2}>
            <Grid size={{ xs: 12, sm: 6 }}>
              <TextField
                label="Institutional Email"
                name="email"
                type="email"
                fullWidth
                size="small"
                placeholder="student@university.edu"
                value={form.email}
                onChange={handleFieldChange}
                disabled={submitting}
                error={Boolean(errors.email)}
                helperText={errors.email}
              />
            </Grid>

            <Grid size={{ xs: 12, sm: 6 }}>
              <TextField
                label="Phone Number"
                name="phone"
                fullWidth
                size="small"
                placeholder="+91 98765 43210"
                value={form.phone}
                onChange={handleFieldChange}
                disabled={submitting}
              />
            </Grid>

            <Grid size={{ xs: 12, sm: 4 }}>
              <TextField
                select
                label="Enrollment Status"
                name="status"
                fullWidth
                size="small"
                value={form.status}
                onChange={handleFieldChange}
                disabled={submitting}
              >
                {STATUS_CHOICES.map((st) => (
                  <MenuItem key={st} value={st}>
                    {st}
                  </MenuItem>
                ))}
              </TextField>
            </Grid>

            <Grid size={{ xs: 12, sm: 4 }}>
              <TextField
                select
                label="Current Semester"
                name="semester"
                fullWidth
                size="small"
                value={form.semester}
                onChange={handleFieldChange}
                disabled={submitting}
              >
                {SEMESTER_CHOICES.map((sem) => (
                  <MenuItem key={sem} value={sem}>
                    Semester {sem}
                  </MenuItem>
                ))}
              </TextField>
            </Grid>

            <Grid size={{ xs: 12, sm: 4 }}>
              <TextField
                label="Academic Year"
                name="academic_year"
                fullWidth
                size="small"
                placeholder="2025-2026"
                value={form.academic_year}
                onChange={handleFieldChange}
                disabled={submitting}
              />
            </Grid>

            <Grid size={{ xs: 12, sm: 4 }}>
              <TextField
                label="CGPA / GPA (0 - 10)"
                name="gpa"
                type="number"
                fullWidth
                size="small"
                slotProps={{ htmlInput: { step: "0.01", min: 0, max: 10 } }}
                value={form.gpa}
                onChange={handleFieldChange}
                disabled={submitting}
                error={Boolean(errors.gpa)}
                helperText={errors.gpa}
              />
            </Grid>

            <Grid size={{ xs: 12, sm: 4 }}>
              <TextField
                label="Attendance (%)"
                name="attendance_pct"
                type="number"
                fullWidth
                size="small"
                slotProps={{ htmlInput: { step: "0.5", min: 0, max: 100 } }}
                value={form.attendance_pct}
                onChange={handleFieldChange}
                disabled={submitting}
                error={Boolean(errors.attendance_pct)}
                helperText={errors.attendance_pct}
              />
            </Grid>

            <Grid size={{ xs: 12, sm: 4 }}>
              <TextField
                label="Admission Date"
                name="admission_date"
                type="date"
                fullWidth
                size="small"
                slotProps={{ inputLabel: { shrink: true } }}
                value={form.admission_date}
                onChange={handleFieldChange}
                disabled={submitting}
              />
            </Grid>
          </Grid>
        </DialogContent>

        <Divider />

        <DialogActions sx={{ px: 3, py: 2 }}>
          <Button
            onClick={onClose}
            disabled={submitting}
            color="inherit"
            sx={{ textTransform: "none", fontWeight: 600 }}
          >
            Cancel
          </Button>
          <Button
            type="submit"
            variant="contained"
            disabled={submitting}
            sx={{
              textTransform: "none",
              fontWeight: 600,
              px: 3,
              borderRadius: 2,
            }}
          >
            {submitting
              ? "Saving..."
              : isEdit
              ? "Save Changes"
              : "Enroll Student"}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}
