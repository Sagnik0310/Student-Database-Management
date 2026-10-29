import React, { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  AppBar,
  Toolbar,
  Typography,
  IconButton,
  Box,
  Drawer,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Tooltip,
  InputBase,
  Badge,
  Menu,
  MenuItem,
  Avatar,
  Chip,
  Divider,
  useMediaQuery,
  useTheme,
} from "@mui/material";
import MenuRoundedIcon from "@mui/icons-material/MenuRounded";
import MenuOpenRoundedIcon from "@mui/icons-material/MenuOpenRounded";
import DashboardRoundedIcon from "@mui/icons-material/DashboardRounded";
import PeopleAltRoundedIcon from "@mui/icons-material/PeopleAltRounded";
import MenuBookRoundedIcon from "@mui/icons-material/MenuBookRounded";
import EventAvailableRoundedIcon from "@mui/icons-material/EventAvailableRounded";
import WorkspacePremiumRoundedIcon from "@mui/icons-material/WorkspacePremiumRounded";
import InsightsRoundedIcon from "@mui/icons-material/InsightsRounded";
import AssessmentRoundedIcon from "@mui/icons-material/AssessmentRounded";
import HistoryRoundedIcon from "@mui/icons-material/HistoryRounded";
import SettingsRoundedIcon from "@mui/icons-material/SettingsRounded";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import DarkModeRoundedIcon from "@mui/icons-material/DarkModeRounded";
import LightModeRoundedIcon from "@mui/icons-material/LightModeRounded";
import NotificationsNoneRoundedIcon from "@mui/icons-material/NotificationsNoneRounded";
import SearchRoundedIcon from "@mui/icons-material/SearchRounded";
import SchoolRoundedIcon from "@mui/icons-material/SchoolRounded";
import FiberManualRecordIcon from "@mui/icons-material/FiberManualRecord";
import LogoutRoundedIcon from "@mui/icons-material/LogoutRounded";

export const DRAWER_WIDTH_EXPANDED = 250;
export const DRAWER_WIDTH_COLLAPSED = 74;

export const NAV_ITEMS = [
  {
    label: "Overview",
    path: "/",
    icon: <DashboardRoundedIcon />,
    roles: ["Admin", "Faculty", "Student"],
  },
  {
    label: "Students",
    path: "/students",
    icon: <PeopleAltRoundedIcon />,
    roles: ["Admin", "Faculty", "Student"],
  },
  {
    label: "Academics",
    path: "/academics",
    icon: <MenuBookRoundedIcon />,
    roles: ["Admin", "Faculty"],
  },
  {
    label: "Attendance",
    path: "/attendance",
    icon: <EventAvailableRoundedIcon />,
    roles: ["Admin", "Faculty", "Student"],
  },
  {
    label: "Performance",
    path: "/performance",
    icon: <WorkspacePremiumRoundedIcon />,
    roles: ["Admin", "Faculty", "Student"],
  },
  {
    label: "Analytics",
    path: "/analytics",
    icon: <InsightsRoundedIcon />,
    roles: ["Admin", "Faculty"],
  },
  {
    label: "Reports",
    path: "/reports",
    icon: <AssessmentRoundedIcon />,
    roles: ["Admin", "Faculty"],
  },
  {
    label: "Activity Logs",
    path: "/logs",
    icon: <HistoryRoundedIcon />,
    roles: ["Admin"],
  },
  {
    label: "Settings",
    path: "/settings",
    icon: <SettingsRoundedIcon />,
    roles: ["Admin", "Faculty", "Student"],
  },
  {
    label: "About",
    path: "/about",
    icon: <InfoOutlinedIcon />,
    roles: ["Admin", "Faculty", "Student"],
  },
];

export default function Navbar({
  darkMode = false,
  onToggleDarkMode,
  sidebarCollapsed = false,
  onToggleSidebar,
  globalSearch = "",
  onGlobalSearchChange,
  apiHealthy = true,
  activityLogs = [],
  currentUser = null,
  onLogout,
}) {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("md"));
  const location = useLocation();
  const navigate = useNavigate();

  const [mobileOpen, setMobileOpen] = useState(false);
  const [notifAnchor, setNotifAnchor] = useState(null);
  const [profileAnchor, setProfileAnchor] = useState(null);

  const userRole = currentUser?.role || "Admin";
  const userFullName = currentUser?.full_name || "System Administrator";
  const userInitials = String(userFullName)
    .split(/\s+/)
    .map((p) => p[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  const visibleNavItems = NAV_ITEMS.filter(
    (item) => !item.roles || item.roles.includes(userRole)
  );

  const drawerWidth = sidebarCollapsed
    ? DRAWER_WIDTH_COLLAPSED
    : DRAWER_WIDTH_EXPANDED;

  const handleNavigate = (path) => {
    navigate(path);
    if (isMobile) {
      setMobileOpen(false);
    }
  };

  const handleSearchInput = (e) => {
    const val = e.target.value;
    if (onGlobalSearchChange) {
      onGlobalSearchChange(val);
    }
    if (val && location.pathname !== "/students" && location.pathname !== "/") {
      navigate("/students");
    }
  };

  const drawerContent = (
    <Box
      sx={{
        height: "100%",
        display: "flex",
        flexDirection: "column",
        bgcolor: "#0f172a",
        color: "#f8fafc",
      }}
    >
      {/* Brand Header */}
      <Box
        sx={{
          height: 64,
          px: sidebarCollapsed && !isMobile ? 1.5 : 2.5,
          display: "flex",
          alignItems: "center",
          justifyContent:
            sidebarCollapsed && !isMobile ? "center" : "space-between",
          borderBottom: "1px solid rgba(255,255,255,0.08)",
        }}
      >
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            gap: 1.5,
            cursor: "pointer",
          }}
          onClick={() => handleNavigate("/")}
        >
          <Box
            sx={{
              width: 38,
              height: 38,
              borderRadius: 2,
              background: "linear-gradient(135deg, #3b82f6 0%, #4f46e5 100%)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#fff",
              flexShrink: 0,
              boxShadow: "0 4px 12px rgba(59, 130, 246, 0.4)",
            }}
          >
            <SchoolRoundedIcon fontSize="small" />
          </Box>
          {(!sidebarCollapsed || isMobile) && (
            <Box>
              <Typography
                variant="subtitle1"
                sx={{
                  fontWeight: 800,
                  letterSpacing: -0.3,
                  lineHeight: 1.1,
                  color: "#ffffff",
                }}
              >
                StudentDB 2.0
              </Typography>
              <Typography
                variant="caption"
                sx={{ color: "rgba(255,255,255,0.6)", fontSize: "0.68rem" }}
              >
                SIMS Enterprise Portal
              </Typography>
            </Box>
          )}
        </Box>
      </Box>

      {/* Navigation Links */}
      <List sx={{ px: 1.25, py: 2, flex: 1 }}>
        {visibleNavItems.map((item) => {
          const isActive =
            item.path === "/"
              ? location.pathname === "/"
              : location.pathname.startsWith(item.path);

          const button = (
            <ListItemButton
              key={item.path}
              onClick={() => handleNavigate(item.path)}
              selected={isActive}
              sx={{
                mb: 0.5,
                borderRadius: 2,
                minHeight: 44,
                px: sidebarCollapsed && !isMobile ? 1.5 : 2,
                justifyContent:
                  sidebarCollapsed && !isMobile ? "center" : "flex-start",
                color: isActive ? "#ffffff" : "rgba(255,255,255,0.7)",
                "&.Mui-selected": {
                  bgcolor: "rgba(59, 130, 246, 0.22)",
                  color: "#ffffff",
                  "&:hover": {
                    bgcolor: "rgba(59, 130, 246, 0.3)",
                  },
                },
                "&:hover": {
                  bgcolor: "rgba(255,255,255,0.06)",
                  color: "#ffffff",
                },
              }}
            >
              <ListItemIcon
                sx={{
                  minWidth: sidebarCollapsed && !isMobile ? 0 : 36,
                  color: isActive ? "#60a5fa" : "rgba(255,255,255,0.65)",
                  justifyContent: "center",
                }}
              >
                {item.icon}
              </ListItemIcon>
              {(!sidebarCollapsed || isMobile) && (
                <ListItemText
                  primary={item.label}
                  primaryTypographyProps={{
                    fontSize: "0.875rem",
                    fontWeight: isActive ? 700 : 500,
                  }}
                />
              )}
            </ListItemButton>
          );

          return sidebarCollapsed && !isMobile ? (
            <Tooltip title={item.label} placement="right" key={item.path}>
              {button}
            </Tooltip>
          ) : (
            button
          );
        })}
      </List>

      {/* Footer Role Card */}
      {(!sidebarCollapsed || isMobile) && (
        <Box
          sx={{
            p: 2,
            m: 1.5,
            borderRadius: 2.5,
            bgcolor: "rgba(255,255,255,0.05)",
            border: "1px solid rgba(255,255,255,0.08)",
          }}
        >
          <Typography
            variant="caption"
            sx={{ color: "rgba(255,255,255,0.55)", display: "block" }}
          >
            SIGNED IN AS
          </Typography>
          <Typography
            variant="body2"
            sx={{ fontWeight: 700, color: "#fff", mt: 0.25 }}
          >
            {userFullName}
          </Typography>
          <Typography
            variant="caption"
            sx={{ color: "#93c5fd", display: "block", mt: 0.25 }}
          >
            Role: {userRole}
            {userRole === "Faculty" && currentUser?.assigned_branches?.length
              ? ` (${currentUser.assigned_branches.join(", ")})`
              : ""}
            {userRole === "Student" && currentUser?.linked_reg_no
              ? ` (${currentUser.linked_reg_no})`
              : ""}
          </Typography>
        </Box>
      )}
    </Box>
  );

  return (
    <>
      <AppBar
        position="fixed"
        elevation={0}
        color="inherit"
        sx={{
          width: { md: `calc(100% - ${drawerWidth}px)` },
          ml: { md: `${drawerWidth}px` },
          bgcolor: "background.paper",
          borderBottom: "1px solid",
          borderColor: "divider",
          transition: theme.transitions.create(["width", "margin"], {
            easing: theme.transitions.easing.sharp,
            duration: theme.transitions.duration.leavingScreen,
          }),
        }}
      >
        <Toolbar sx={{ justifyContent: "space-between", gap: 2 }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, flex: 1 }}>
            <IconButton
              edge="start"
              onClick={() => {
                if (isMobile) {
                  setMobileOpen(!mobileOpen);
                } else if (onToggleSidebar) {
                  onToggleSidebar();
                }
              }}
              aria-label="Toggle navigation sidebar"
            >
              {sidebarCollapsed ? <MenuRoundedIcon /> : <MenuOpenRoundedIcon />}
            </IconButton>

            {/* Global Quick Search Bar */}
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                bgcolor: "action.hover",
                borderRadius: 2,
                px: 1.5,
                py: 0.5,
                width: { xs: "100%", sm: 320, md: 380 },
                border: "1px solid",
                borderColor: "divider",
              }}
            >
              <SearchRoundedIcon
                fontSize="small"
                sx={{ color: "text.secondary", mr: 1 }}
              />
              <InputBase
                placeholder="Quick search students (Reg No, Name, Branch)..."
                value={globalSearch}
                onChange={handleSearchInput}
                sx={{ fontSize: "0.875rem", width: "100%" }}
                inputProps={{ "aria-label": "Global quick search" }}
              />
            </Box>
          </Box>

          {/* Right Action Controls */}
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <Chip
              label={`Role: ${userRole}`}
              size="small"
              color={
                userRole === "Admin"
                  ? "primary"
                  : userRole === "Faculty"
                  ? "secondary"
                  : "default"
              }
              sx={{
                display: { xs: "none", md: "inline-flex" },
                fontWeight: 700,
                fontSize: "0.72rem",
              }}
            />

            <Chip
              icon={
                <FiberManualRecordIcon
                  sx={{
                    fontSize: "10px !important",
                    color: apiHealthy
                      ? "#10b981 !important"
                      : "#f59e0b !important",
                  }}
                />
              }
              label={apiHealthy ? "API Connected" : "API Offline"}
              size="small"
              variant="outlined"
              sx={{
                display: { xs: "none", sm: "inline-flex" },
                fontWeight: 600,
                fontSize: "0.75rem",
              }}
            />

            <Tooltip
              title={darkMode ? "Switch to Light Mode" : "Switch to Dark Mode"}
            >
              <IconButton
                onClick={onToggleDarkMode}
                aria-label="Toggle color theme"
              >
                {darkMode ? (
                  <LightModeRoundedIcon fontSize="small" />
                ) : (
                  <DarkModeRoundedIcon fontSize="small" />
                )}
              </IconButton>
            </Tooltip>

            <Tooltip title="Recent Activity Notifications">
              <IconButton
                onClick={(e) => setNotifAnchor(e.currentTarget)}
                aria-label="Open notifications"
              >
                <Badge
                  badgeContent={Math.min(activityLogs.length, 9)}
                  color="primary"
                >
                  <NotificationsNoneRoundedIcon fontSize="small" />
                </Badge>
              </IconButton>
            </Tooltip>

            <Tooltip title={`${userFullName} (${userRole})`}>
              <IconButton
                onClick={(e) => setProfileAnchor(e.currentTarget)}
                size="small"
                sx={{ ml: 0.5 }}
                aria-label="Open user menu"
              >
                <Avatar
                  sx={{
                    width: 34,
                    height: 34,
                    bgcolor: "primary.main",
                    fontSize: "0.85rem",
                    fontWeight: 700,
                  }}
                >
                  {userInitials || "US"}
                </Avatar>
              </IconButton>
            </Tooltip>
          </Box>
        </Toolbar>
      </AppBar>

      {/* Notifications Menu */}
      <Menu
        anchorEl={notifAnchor}
        open={Boolean(notifAnchor)}
        onClose={() => setNotifAnchor(null)}
        PaperProps={{
          sx: { width: 320, maxHeight: 380, borderRadius: 2.5, mt: 1 },
        }}
      >
        <Box sx={{ px: 2, py: 1.5 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
            Recent System Activity
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Audit trail of student database operations
          </Typography>
        </Box>
        <Divider />
        {activityLogs.length === 0 ? (
          <Box sx={{ p: 3, textAlign: "center" }}>
            <Typography variant="body2" color="text.secondary">
              No recent activity recorded yet.
            </Typography>
          </Box>
        ) : (
          activityLogs.slice(0, 5).map((log) => (
            <MenuItem
              key={log.id}
              onClick={() => {
                setNotifAnchor(null);
                if (userRole === "Admin") handleNavigate("/logs");
              }}
              sx={{ whiteSpace: "normal", py: 1.25 }}
            >
              <Box>
                <Typography variant="body2" sx={{ fontWeight: 600 }}>
                  {log.action}
                </Typography>
                <Typography
                  variant="caption"
                  color="text.secondary"
                  display="block"
                >
                  {log.details}
                </Typography>
              </Box>
            </MenuItem>
          ))
        )}
      </Menu>

      {/* Profile Menu */}
      <Menu
        anchorEl={profileAnchor}
        open={Boolean(profileAnchor)}
        onClose={() => setProfileAnchor(null)}
        PaperProps={{ sx: { width: 240, borderRadius: 2.5, mt: 1 } }}
      >
        <Box sx={{ px: 2, py: 1.5 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
            {userFullName}
          </Typography>
          <Typography variant="caption" color="text.secondary" display="block">
            @{currentUser?.username || "admin"} • {userRole}
          </Typography>
        </Box>
        <Divider />
        <MenuItem
          onClick={() => {
            setProfileAnchor(null);
            handleNavigate("/settings");
          }}
        >
          Account & Platform Settings
        </MenuItem>
        <MenuItem
          onClick={() => {
            setProfileAnchor(null);
            handleNavigate("/about");
          }}
        >
          About System 2.0
        </MenuItem>
        {onLogout && <Divider />}
        {onLogout && (
          <MenuItem
            onClick={() => {
              setProfileAnchor(null);
              onLogout();
            }}
            sx={{ color: "error.main", fontWeight: 600, gap: 1 }}
          >
            <LogoutRoundedIcon fontSize="small" />
            Sign Out
          </MenuItem>
        )}
      </Menu>

      {/* Sidebar Drawer */}
      <Box
        component="nav"
        sx={{ width: { md: drawerWidth }, flexShrink: { md: 0 } }}
        aria-label="Main navigation"
      >
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={() => setMobileOpen(false)}
          ModalProps={{ keepMounted: true }}
          sx={{
            display: { xs: "block", md: "none" },
            "& .MuiDrawer-paper": {
              boxSizing: "border-box",
              width: DRAWER_WIDTH_EXPANDED,
              borderRight: "none",
            },
          }}
        >
          {drawerContent}
        </Drawer>

        <Drawer
          variant="permanent"
          open
          sx={{
            display: { xs: "none", md: "block" },
            "& .MuiDrawer-paper": {
              boxSizing: "border-box",
              width: drawerWidth,
              borderRight: "none",
              transition: theme.transitions.create("width", {
                easing: theme.transitions.easing.sharp,
                duration: theme.transitions.duration.leavingScreen,
              }),
              overflowX: "hidden",
            },
          }}
        >
          {drawerContent}
        </Drawer>
      </Box>
    </>
  );
}
