import React from "react";
import {
  Card,
  CardContent,
  Typography,
  Box,
  Grid,
  Skeleton,
  Chip,
} from "@mui/material";
import PeopleAltRoundedIcon from "@mui/icons-material/PeopleAltRounded";
import AccountTreeRoundedIcon from "@mui/icons-material/AccountTreeRounded";
import SchoolRoundedIcon from "@mui/icons-material/SchoolRounded";
import VerifiedUserRoundedIcon from "@mui/icons-material/VerifiedUserRounded";

export default function DashboardCards({ students = [], loading = false }) {
  const safeStudents = Array.isArray(students) ? students : [];
  const totalStudents = safeStudents.length;

  const activeStudents = safeStudents.filter(
    (s) => !s.status || s.status === "Active"
  ).length;

  const uniqueBranches = new Set(
    safeStudents
      .map((s) => (s.branch || "").trim().toUpperCase())
      .filter(Boolean)
  ).size;

  const validAges = safeStudents
    .map((s) => Number(s.age))
    .filter((a) => !Number.isNaN(a) && a > 0);

  const avgAge =
    validAges.length > 0
      ? (validAges.reduce((acc, v) => acc + v, 0) / validAges.length).toFixed(1)
      : "0.0";

  const validGpas = safeStudents
    .map((s) => (s.gpa !== null && s.gpa !== undefined && s.gpa !== "" ? Number(s.gpa) : NaN))
    .filter((g) => !Number.isNaN(g) && g >= 0);

  const avgGpa =
    validGpas.length > 0
      ? (validGpas.reduce((acc, v) => acc + v, 0) / validGpas.length).toFixed(2)
      : null;

  const activeRate =
    totalStudents > 0 ? Math.round((activeStudents / totalStudents) * 100) : 100;

  const cards = [
    {
      title: "Total Students",
      value: totalStudents,
      subtitle: `${activeStudents} Active enrolled`,
      badge: `${activeRate}% Active`,
      icon: <PeopleAltRoundedIcon fontSize="medium" />,
      accent: "#1e40af",
      bgLight: "rgba(30, 64, 175, 0.12)",
    },
    {
      title: "Academic Branches",
      value: uniqueBranches,
      subtitle: "Departments represented",
      badge: uniqueBranches > 0 ? "Active Depts" : "No Depts",
      icon: <AccountTreeRoundedIcon fontSize="medium" />,
      accent: "#4338ca",
      bgLight: "rgba(67, 56, 202, 0.12)",
    },
    {
      title: "Average Student Age",
      value: `${avgAge} yrs`,
      subtitle:
        validAges.length > 0
          ? `Range: ${Math.min(...validAges)}–${Math.max(...validAges)} yrs`
          : "Based on enrolled records",
      badge: "Demographics",
      icon: <SchoolRoundedIcon fontSize="medium" />,
      accent: "#0284c7",
      bgLight: "rgba(2, 132, 199, 0.12)",
    },
    {
      title: avgGpa ? "Average Cohort GPA" : "Enrollment Status",
      value: avgGpa ? `${avgGpa} / 10` : `${activeRate}%`,
      subtitle: avgGpa
        ? `Across ${validGpas.length} graded record(s)`
        : `${activeStudents} of ${totalStudents} active`,
      badge: avgGpa ? "Academic Index" : "Verified Records",
      icon: <VerifiedUserRoundedIcon fontSize="medium" />,
      accent: "#0d9488",
      bgLight: "rgba(13, 148, 136, 0.12)",
    },
  ];

  return (
    <Grid container spacing={2.5} sx={{ mb: 3 }}>
      {cards.map((item) => (
        <Grid size={{ xs: 12, sm: 6, lg: 3 }} key={item.title}>
          <Card
            elevation={0}
            sx={{
              height: "100%",
              borderRadius: 3,
              border: "1px solid",
              borderColor: "divider",
              transition: "transform 0.2s ease, box-shadow 0.2s ease",
              "&:hover": {
                transform: "translateY(-2px)",
                boxShadow: "0 10px 24px rgba(15, 23, 42, 0.08)",
              },
            }}
          >
            <CardContent sx={{ p: 2.5 }}>
              <Box
                sx={{
                  display: "flex",
                  alignItems: "flex-start",
                  justifyContent: "space-between",
                  mb: 1.5,
                }}
              >
                <Box>
                  <Typography
                    variant="subtitle2"
                    color="text.secondary"
                    sx={{ fontWeight: 600, letterSpacing: 0.2 }}
                  >
                    {item.title}
                  </Typography>
                  {loading ? (
                    <Skeleton variant="text" width={90} height={44} />
                  ) : (
                    <Typography
                      variant="h4"
                      sx={{
                        fontWeight: 800,
                        mt: 0.5,
                        color: "text.primary",
                        letterSpacing: -0.5,
                      }}
                    >
                      {item.value}
                    </Typography>
                  )}
                </Box>
                <Box
                  sx={{
                    width: 44,
                    height: 44,
                    borderRadius: 2.5,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    bgcolor: item.bgLight,
                    color: item.accent,
                  }}
                >
                  {item.icon}
                </Box>
              </Box>

              <Box
                sx={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  mt: 1.5,
                  pt: 1.5,
                  borderTop: "1px dashed",
                  borderColor: "divider",
                }}
              >
                <Typography variant="caption" color="text.secondary">
                  {item.subtitle}
                </Typography>
                <Chip
                  label={item.badge}
                  size="small"
                  sx={{
                    height: 22,
                    fontSize: "0.7rem",
                    fontWeight: 600,
                    bgcolor: item.bgLight,
                    color: item.accent,
                  }}
                />
              </Box>
            </CardContent>
          </Card>
        </Grid>
      ))}
    </Grid>
  );
}
