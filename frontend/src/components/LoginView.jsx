import React, { useState } from "react";
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  Alert,
  InputAdornment,
  IconButton,
  Chip,
  Stack,
  Divider,
} from "@mui/material";
import SchoolRoundedIcon from "@mui/icons-material/SchoolRounded";
import LockOutlinedIcon from "@mui/icons-material/LockOutlined";
import PersonOutlineRoundedIcon from "@mui/icons-material/PersonOutlineRounded";
import VisibilityRoundedIcon from "@mui/icons-material/VisibilityRounded";
import VisibilityOffRoundedIcon from "@mui/icons-material/VisibilityOffRounded";
import VerifiedUserRoundedIcon from "@mui/icons-material/VerifiedUserRounded";

export default function LoginView({ onLogin, loading = false, error = "" }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [localError, setLocalError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLocalError("");
    if (!username.trim() || !password) {
      setLocalError("Please enter both username and password");
      return;
    }
    try {
      await onLogin(username.trim(), password);
    } catch (err) {
      setLocalError(err?.message || "Invalid credentials");
    }
  };

  const fillRolePreset = (u, p) => {
    setUsername(u);
    setPassword(p);
    setLocalError("");
  };

  const displayError = localError || error;

  return (
    <Box
      sx={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        p: 2,
        background:
          "linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #1e3a8a 100%)",
      }}
    >
      <Paper
        elevation={8}
        sx={{
          width: "100%",
          maxWidth: 440,
          p: { xs: 3, sm: 4 },
          borderRadius: 3.5,
        }}
      >
        <Box sx={{ textAlign: "center", mb: 3 }}>
          <Box
            sx={{
              width: 52,
              height: 52,
              borderRadius: 2.5,
              background: "linear-gradient(135deg, #2563eb 0%, #4f46e5 100%)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#fff",
              mx: "auto",
              mb: 1.5,
              boxShadow: "0 8px 20px rgba(37, 99, 235, 0.35)",
            }}
          >
            <SchoolRoundedIcon fontSize="medium" />
          </Box>
          <Typography variant="h5" sx={{ fontWeight: 800, letterSpacing: -0.4 }}>
            StudentDB 2.0 Portal
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            Sign in with your authorized institutional account
          </Typography>
        </Box>

        {displayError && (
          <Alert severity="error" sx={{ mb: 2.5, borderRadius: 2 }}>
            {displayError}
          </Alert>
        )}

        <form onSubmit={handleSubmit} noValidate>
          <Stack spacing={2}>
            <TextField
              label="Username"
              fullWidth
              size="small"
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              disabled={loading}
              slotProps={{
                input: {
                  startAdornment: (
                    <InputAdornment position="start">
                      <PersonOutlineRoundedIcon fontSize="small" />
                    </InputAdornment>
                  ),
                },
              }}
            />

            <TextField
              label="Password"
              type={showPassword ? "text" : "password"}
              fullWidth
              size="small"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={loading}
              slotProps={{
                input: {
                  startAdornment: (
                    <InputAdornment position="start">
                      <LockOutlinedIcon fontSize="small" />
                    </InputAdornment>
                  ),
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton
                        size="small"
                        onClick={() => setShowPassword((prev) => !prev)}
                        aria-label={
                          showPassword ? "Hide password" : "Show password"
                        }
                      >
                        {showPassword ? (
                          <VisibilityOffRoundedIcon fontSize="small" />
                        ) : (
                          <VisibilityRoundedIcon fontSize="small" />
                        )}
                      </IconButton>
                    </InputAdornment>
                  ),
                },
              }}
            />

            <Button
              type="submit"
              variant="contained"
              fullWidth
              disabled={loading}
              sx={{
                py: 1.2,
                fontWeight: 700,
                textTransform: "none",
                borderRadius: 2,
              }}
            >
              {loading ? "Signing In..." : "Sign In"}
            </Button>
          </Stack>
        </form>

        <Divider sx={{ my: 2.5 }} />

        <Box>
          <Box sx={{ display: "flex", alignItems: "center", gap: 0.75, mb: 1 }}>
            <VerifiedUserRoundedIcon fontSize="small" color="primary" />
            <Typography variant="caption" sx={{ fontWeight: 700 }}>
              Role-Based Access Control (RBAC) Quick Fill
            </Typography>
          </Box>
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            <Chip
              label="Admin (Full Access)"
              size="small"
              variant="outlined"
              color="primary"
              onClick={() => fillRolePreset("admin", "Admin@123")}
            />
            <Chip
              label="Faculty (CSE Dept)"
              size="small"
              variant="outlined"
              color="secondary"
              onClick={() => fillRolePreset("faculty_cse", "Faculty@123")}
            />
            <Chip
              label="Student (Own Record)"
              size="small"
              variant="outlined"
              onClick={() => fillRolePreset("student_demo", "Student@123")}
            />
          </Stack>
        </Box>
      </Paper>
    </Box>
  );
}

