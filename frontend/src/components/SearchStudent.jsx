import React from "react";
import {
  Box,
  TextField,
  InputAdornment,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Button,
  IconButton,
  Tooltip,
  Chip,
  Paper,
  Stack,
} from "@mui/material";
import SearchRoundedIcon from "@mui/icons-material/SearchRounded";
import ClearRoundedIcon from "@mui/icons-material/ClearRounded";
import FilterAltOffRoundedIcon from "@mui/icons-material/FilterAltOffRounded";
import PersonAddAlt1RoundedIcon from "@mui/icons-material/PersonAddAlt1Rounded";
import FileUploadRoundedIcon from "@mui/icons-material/FileUploadRounded";
import FileDownloadRoundedIcon from "@mui/icons-material/FileDownloadRounded";
import RefreshRoundedIcon from "@mui/icons-material/RefreshRounded";

const STATUS_OPTIONS = ["All", "Active", "On Leave", "Probation", "Graduated", "Inactive"];
const SEMESTER_OPTIONS = ["All", "1", "2", "3", "4", "5", "6", "7", "8"];

export default function SearchStudent({
  searchQuery = "",
  onSearchChange,
  branchFilter = "All",
  onBranchChange,
  statusFilter = "All",
  onStatusChange,
  semesterFilter = "All",
  onSemesterChange,
  branches = [],
  totalCount = 0,
  filteredCount = 0,
  onResetFilters,
  onOpenAddModal,
  onOpenImportModal,
  onExportCsv,
  onRefresh,
  loading = false,
}) {
  const hasActiveFilters =
    Boolean(searchQuery?.trim()) ||
    branchFilter !== "All" ||
    statusFilter !== "All" ||
    semesterFilter !== "All";

  return (
    <Paper
      elevation={0}
      sx={{
        p: { xs: 2, md: 2.5 },
        mb: 3,
        borderRadius: 3,
        border: "1px solid",
        borderColor: "divider",
      }}
    >
      <Stack
        direction={{ xs: "column", lg: "row" }}
        spacing={2}
        alignItems={{ xs: "stretch", lg: "center" }}
        justifyContent="space-between"
      >
        {/* Search and Filter Controls */}
        <Stack
          direction={{ xs: "column", sm: "row" }}
          spacing={1.5}
           sx={{ flex: 1 }}
          useFlexGap
          flexWrap="wrap"
        >
          <TextField
            size="small"
            placeholder="Search by Reg No, Roll No, Name, or Branch..."
            value={searchQuery}
            onChange={(e) => onSearchChange && onSearchChange(e.target.value)}
            sx={{ minWidth: { xs: "100%", sm: 280, md: 320 }, flex: 1 }}
            slotProps={{
              input: {
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchRoundedIcon fontSize="small" color="action" />
                  </InputAdornment>
                ),
                endAdornment: searchQuery ? (
                  <InputAdornment position="end">
                    <IconButton
                      size="small"
                      aria-label="Clear search"
                      onClick={() => onSearchChange && onSearchChange("")}
                    >
                      <ClearRoundedIcon fontSize="small" />
                    </IconButton>
                  </InputAdornment>
                ) : null,
              },
            }}
          />

          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel id="branch-filter-label">Branch</InputLabel>
            <Select
              labelId="branch-filter-label"
              label="Branch"
              value={branchFilter}
              onChange={(e) => onBranchChange && onBranchChange(e.target.value)}
            >
              <MenuItem value="All">All Branches</MenuItem>
              {branches.map((b) => (
                <MenuItem key={b} value={b}>
                  {b}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <FormControl size="small" sx={{ minWidth: 140 }}>
            <InputLabel id="status-filter-label">Status</InputLabel>
            <Select
              labelId="status-filter-label"
              label="Status"
              value={statusFilter}
              onChange={(e) => onStatusChange && onStatusChange(e.target.value)}
            >
              {STATUS_OPTIONS.map((status) => (
                <MenuItem key={status} value={status}>
                  {status === "All" ? "All Statuses" : status}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <FormControl size="small" sx={{ minWidth: 130 }}>
            <InputLabel id="semester-filter-label">Semester</InputLabel>
            <Select
              labelId="semester-filter-label"
              label="Semester"
              value={semesterFilter}
              onChange={(e) =>
                onSemesterChange && onSemesterChange(e.target.value)
              }
            >
              {SEMESTER_OPTIONS.map((sem) => (
                <MenuItem key={sem} value={sem}>
                  {sem === "All" ? "All Semesters" : `Semester ${sem}`}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          {hasActiveFilters && (
            <Button
              variant="text"
              color="inherit"
              size="small"
              startIcon={<FilterAltOffRoundedIcon />}
              onClick={onResetFilters}
              sx={{ textTransform: "none", fontWeight: 600 }}
            >
              Reset
            </Button>
          )}
        </Stack>

        {/* Action Toolbar Buttons */}
        <Stack
          direction="row"
          spacing={1.25}
          alignItems="center"
          justifyContent={{ xs: "flex-start", lg: "flex-end" }}
          flexWrap="wrap"
          useFlexGap
        >
          <Tooltip title="Reload records from database">
            <span>
              <IconButton
                onClick={onRefresh}
                disabled={loading}
                aria-label="Refresh students"
                sx={{
                  border: "1px solid",
                  borderColor: "divider",
                  borderRadius: 2,
                }}
              >
                <RefreshRoundedIcon fontSize="small" />
              </IconButton>
            </span>
          </Tooltip>

          {onOpenImportModal && (
            <Button
              variant="outlined"
              size="small"
              startIcon={<FileUploadRoundedIcon />}
              onClick={onOpenImportModal}
              sx={{
                textTransform: "none",
                fontWeight: 600,
                borderRadius: 2,
                py: 0.9,
              }}
            >
              Import CSV
            </Button>
          )}

          {onExportCsv && (
            <Button
              variant="outlined"
              size="small"
              startIcon={<FileDownloadRoundedIcon />}
              onClick={onExportCsv}
              sx={{
                textTransform: "none",
                fontWeight: 600,
                borderRadius: 2,
                py: 0.9,
              }}
            >
              Export CSV
            </Button>
          )}

          {onOpenAddModal && (
            <Button
              variant="contained"
              size="small"
              startIcon={<PersonAddAlt1RoundedIcon />}
              onClick={onOpenAddModal}
              sx={{
                textTransform: "none",
                fontWeight: 600,
                borderRadius: 2,
                py: 0.9,
                px: 2,
                boxShadow: "none",
              }}
            >
              Add Student
            </Button>
          )}
        </Stack>
      </Stack>

      {/* Active filter summary bar */}
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: 1,
          mt: 1.5,
          pt: 1.5,
          borderTop: "1px solid",
          borderColor: "divider",
          fontSize: "0.8rem",
          color: "text.secondary",
        }}
      >
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}>
          <span>
            Showing <strong>{filteredCount}</strong> of{" "}
            <strong>{totalCount}</strong> student record(s)
          </span>
          {searchQuery?.trim() && (
            <Chip
              size="small"
              label={`Search: "${searchQuery.trim()}"`}
              onDelete={() => onSearchChange && onSearchChange("")}
            />
          )}
          {branchFilter !== "All" && (
            <Chip
              size="small"
              label={`Branch: ${branchFilter}`}
              onDelete={() => onBranchChange && onBranchChange("All")}
            />
          )}
          {statusFilter !== "All" && (
            <Chip
              size="small"
              label={`Status: ${statusFilter}`}
              onDelete={() => onStatusChange && onStatusChange("All")}
            />
          )}
          {semesterFilter !== "All" && (
            <Chip
              size="small"
              label={`Semester: ${semesterFilter}`}
              onDelete={() => onSemesterChange && onSemesterChange("All")}
            />
          )}
        </Box>
      </Box>
    </Paper>
  );
}
