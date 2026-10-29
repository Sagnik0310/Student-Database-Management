import React from "react";
import {
  Box,
  Typography,
  Paper,
  Grid,
  Chip,
  Stack,
  Divider,
} from "@mui/material";
import StorageRoundedIcon from "@mui/icons-material/StorageRounded";
import SecurityRoundedIcon from "@mui/icons-material/SecurityRounded";
import InsightsRoundedIcon from "@mui/icons-material/InsightsRounded";
import TerminalRoundedIcon from "@mui/icons-material/TerminalRounded";

const PILLARS = [
  {
    title: "Unified Full-Stack Architecture",
    desc: "React 19 & Material UI 7 SPA paired with a Python Flask REST API and shared business service layer.",
    icon: <StorageRoundedIcon color="primary" />,
  },
  {
    title: "Real-Time MongoDB Analytics",
    desc: "Live departmental distributions, attendance compliance, and CGPA metrics computed directly from MongoDB documents.",
    icon: <InsightsRoundedIcon color="primary" />,
  },
  {
    title: "Data Integrity & Validation",
    desc: "Strict alphanumeric registration-number validation, duplicate prevention, unique indexes, and confirmation modals.",
    icon: <SecurityRoundedIcon color="primary" />,
  },
  {
    title: "Dual Web & CLI Interfaces",
    desc: "Seamless interoperability between the web administrative dashboard and the interactive Python CLI (main.py).",
    icon: <TerminalRoundedIcon color="primary" />,
  },
];

export default function About() {
  return (
    <Box className="dashboard-container">
      <Paper
        elevation={0}
        sx={{
          p: { xs: 3, md: 4 },
          mb: 3,
          borderRadius: 3,
          border: "1px solid",
          borderColor: "divider",
        }}
      >
        <Chip
          label="Platform Release 2.0"
          color="primary"
          size="small"
          sx={{ fontWeight: 700, mb: 1.5 }}
        />
        <Typography variant="h4" sx={{ fontWeight: 800, mb: 1 }}>
          About This Project
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ maxWidth: 760 }}>
          The <strong>Student Database Management System 2.0</strong> is a
          modern, full-stack Student Information Management Platform built with
          React, Material UI, Flask, PyMongo, and MongoDB. It provides
          administrators with real-time CRUD operations, multi-criteria filtering,
          bulk CSV import/export, attendance and CGPA tracking, and department
          analytics.
        </Typography>

        <Divider sx={{ my: 3 }} />

        <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1.5 }}>
          Core Technology Stack
        </Typography>
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
          {[
            "React 19",
            "Material UI 7",
            "React Router 6",
            "Recharts",
            "Python 3.11",
            "Flask REST API",
            "PyMongo",
            "MongoDB Atlas",
            "Gunicorn",
            "Render Cloud",
          ].map((tech) => (
            <Chip key={tech} label={tech} variant="outlined" size="small" />
          ))}
        </Stack>
      </Paper>

      <Grid container spacing={2.5}>
        {PILLARS.map((item) => (
          <Grid size={{ xs: 12, sm: 6 }} key={item.title}>
            <Paper
              elevation={0}
              sx={{
                p: 3,
                height: "100%",
                borderRadius: 3,
                border: "1px solid",
                borderColor: "divider",
              }}
            >
              <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, mb: 1 }}>
                {item.icon}
                <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
                  {item.title}
                </Typography>
              </Box>
              <Typography variant="body2" color="text.secondary">
                {item.desc}
              </Typography>
            </Paper>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
}
