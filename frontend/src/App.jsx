import React, { useState, useEffect, useMemo } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { ThemeProvider, createTheme, CssBaseline, Box } from "@mui/material";
import "./App.css";
import Navbar, {
  DRAWER_WIDTH_EXPANDED,
  DRAWER_WIDTH_COLLAPSED,
} from "./components/Navbar";
import LoginView from "./components/LoginView";
import Dashboard from "./pages/Dashboard";
import About from "./pages/About";
import {
  getActivityLogs,
  getCurrentUser,
  subscribeAuthChange,
  loginUser,
  logoutUser,
  fetchCurrentUser,
} from "./services/api";

function App({ initialUser = undefined }) {
  const [darkMode, setDarkMode] = useState(() => {
    try {
      return localStorage.getItem("studentdb_theme_mode") === "dark";
    } catch {
      return false;
    }
  });

  const [currentUser, setCurrentUser] = useState(() =>
    initialUser !== undefined ? initialUser : getCurrentUser()
  );
  const [authRequired, setAuthRequired] = useState(() =>
    initialUser !== undefined ? initialUser === null : !getCurrentUser()
  );
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState("");

  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [globalSearch, setGlobalSearch] = useState("");
  const [apiHealthy, setApiHealthy] = useState(true);
  const [activityLogs, setActivityLogs] = useState(() => getActivityLogs());

  useEffect(() => {
    const unsubscribe = subscribeAuthChange((user) => {
      if (user) {
        setCurrentUser(user);
        setAuthRequired(false);
      } else {
        setCurrentUser(null);
        setAuthRequired(true);
      }
    });
    return unsubscribe;
  }, []);

  useEffect(() => {
    if (initialUser !== undefined) return;
    let mounted = true;
    fetchCurrentUser()
      .then((user) => {
        if (mounted && user) {
          setCurrentUser(user);
          setAuthRequired(false);
        }
      })
      .catch(() => {
        // Handled by apiFetch 401 listener if backend requires login
      });
    return () => {
      mounted = false;
    };
  }, [initialUser]);

  const handleLogin = async (username, password) => {
    setAuthLoading(true);
    setAuthError("");
    try {
      const res = await loginUser(username, password);
      setCurrentUser(res.user);
      setAuthRequired(false);
      setActivityLogs(getActivityLogs());
    } catch (err) {
      setAuthError(err.message || "Authentication failed");
      throw err;
    } finally {
      setAuthLoading(false);
    }
  };

  const handleLogout = async () => {
    await logoutUser();
    setCurrentUser(null);
    setAuthRequired(true);
  };

  const handleToggleDarkMode = () => {
    setDarkMode((prev) => {
      const next = !prev;
      try {
        localStorage.setItem("studentdb_theme_mode", next ? "dark" : "light");
      } catch {
        // ignore storage errors
      }
      return next;
    });
  };

  const theme = useMemo(
    () =>
      createTheme({
        palette: {
          mode: darkMode ? "dark" : "light",
          primary: {
            main: darkMode ? "#3b82f6" : "#2563eb",
            dark: "#1d4ed8",
            light: "#60a5fa",
          },
          secondary: {
            main: "#4f46e5",
          },
          background: {
            default: darkMode ? "#0b1120" : "#f1f5f9",
            paper: darkMode ? "#111827" : "#ffffff",
          },
        },
        typography: {
          fontFamily:
            "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
        },
        shape: {
          borderRadius: 10,
        },
      }),
    [darkMode]
  );

  if (authRequired || !currentUser) {
    return (
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <LoginView
          onLogin={handleLogin}
          loading={authLoading}
          error={authError}
        />
      </ThemeProvider>
    );
  }

  const drawerWidth = sidebarCollapsed
    ? DRAWER_WIDTH_COLLAPSED
    : DRAWER_WIDTH_EXPANDED;

  const dashboardProps = {
    currentUser,
    globalSearch,
    onGlobalSearchChange: setGlobalSearch,
    darkMode,
    onToggleDarkMode: handleToggleDarkMode,
    onLogsUpdated: setActivityLogs,
    onApiStatusChange: setApiHealthy,
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <BrowserRouter
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
      >
        <Box sx={{ display: "flex", minHeight: "100vh" }}>
          <Navbar
            darkMode={darkMode}
            onToggleDarkMode={handleToggleDarkMode}
            sidebarCollapsed={sidebarCollapsed}
            onToggleSidebar={() => setSidebarCollapsed((prev) => !prev)}
            globalSearch={globalSearch}
            onGlobalSearchChange={setGlobalSearch}
            apiHealthy={apiHealthy}
            activityLogs={activityLogs}
            currentUser={currentUser}
            onLogout={handleLogout}
          />

          <Box
            component="main"
            sx={{
              flexGrow: 1,
              width: { md: `calc(100% - ${drawerWidth}px)` },
              pt: { xs: 9, md: 10 },
              pb: 6,
              px: { xs: 2, sm: 3, md: 4 },
              overflowX: "hidden",
            }}
          >
            <Routes>
              <Route path="/" element={<Dashboard {...dashboardProps} />} />
              <Route
                path="/students/*"
                element={<Dashboard {...dashboardProps} />}
              />
              <Route
                path="/academics/*"
                element={<Dashboard {...dashboardProps} />}
              />
              <Route
                path="/attendance/*"
                element={<Dashboard {...dashboardProps} />}
              />
              <Route
                path="/performance/*"
                element={<Dashboard {...dashboardProps} />}
              />
              <Route
                path="/analytics/*"
                element={<Dashboard {...dashboardProps} />}
              />
              <Route
                path="/reports/*"
                element={<Dashboard {...dashboardProps} />}
              />
              <Route
                path="/logs/*"
                element={<Dashboard {...dashboardProps} />}
              />
              <Route
                path="/settings/*"
                element={<Dashboard {...dashboardProps} />}
              />
              <Route path="/about/*" element={<About />} />
              <Route path="*" element={<Dashboard {...dashboardProps} />} />
            </Routes>
          </Box>
        </Box>
      </BrowserRouter>
    </ThemeProvider>
  );
}

export default App;
