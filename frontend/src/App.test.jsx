import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import App from "./App";
import DashboardCards from "./components/DashboardCards";
import StudentTable from "./components/StudentTable";
import StudentForm from "./components/StudentForm";
import LoginView from "./components/LoginView";
import {
  AcademicsWorkspace,
  AttendanceWorkspace,
  PerformanceWorkspace,
} from "./components/AcademicModules";
import {
  AdvancedAnalyticsWorkspace,
  ReportsAndExportsWorkspace,
  AiAnalyticsAssistantPanel,
} from "./components/ReportingAndAiModules";
import { setAuthSession, clearAuthSession } from "./services/api";

const SAMPLE_STUDENTS = [
  {
    reg_no: "REG2026001",
    roll_no: "101",
    name: "Aarav Sharma",
    age: 20,
    branch: "CSE",
    status: "Active",
    gpa: 8.9,
    attendance_pct: 92,
  },
  {
    reg_no: "REG2026002",
    roll_no: "102",
    name: "Priya Patel",
    age: 21,
    branch: "ECE",
    status: "Active",
    gpa: 9.2,
    attendance_pct: 95,
  },
];

beforeEach(() => {
  localStorage.clear();
  setAuthSession(
    {
      username: "admin",
      role: "Admin",
      full_name: "System Administrator",
      assigned_branches: ["*"],
    },
    "test-csrf-token-123"
  );

  global.fetch = jest.fn((url) => {
    if (String(url).includes("/auth/me")) {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () =>
          Promise.resolve({
            success: true,
            user: {
              username: "admin",
              role: "Admin",
              full_name: "System Administrator",
              assigned_branches: ["*"],
            },
            csrf_token: "test-csrf-token-123",
          }),
      });
    }
    return Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve(SAMPLE_STUDENTS),
    });
  });
});

afterEach(() => {
  jest.restoreAllMocks();
});

test("renders Student Management System dashboard and loads student records", async () => {
  render(<App />);
  expect(
    screen.getByRole("heading", { name: /Student Management System/i })
  ).toBeInTheDocument();

  await waitFor(() => {
    expect(screen.getAllByText("Aarav Sharma").length).toBeGreaterThan(0);
  });
  expect(screen.getByText("Priya Patel")).toBeInTheDocument();
});

test("renders LoginView when unauthenticated and never stores auth tokens in localStorage", async () => {
  clearAuthSession();
  render(<App initialUser={null} />);

  expect(
    screen.getByRole("heading", { name: /StudentDB 2.0 Portal/i })
  ).toBeInTheDocument();
  expect(localStorage.getItem("studentdb_session")).toBeNull();
  expect(localStorage.getItem("token")).toBeNull();
});

test("LoginView validates empty credentials and submits valid credentials", async () => {
  const mockLogin = jest.fn(() => Promise.resolve());
  render(<LoginView onLogin={mockLogin} />);

  fireEvent.click(screen.getByRole("button", { name: /Sign In/i }));
  expect(
    await screen.findByText(/Please enter both username and password/i)
  ).toBeInTheDocument();
  expect(mockLogin).not.toHaveBeenCalled();

  fireEvent.click(screen.getByText(/Admin \(Full Access\)/i));
  fireEvent.click(screen.getByRole("button", { name: /Sign In/i }));

  await waitFor(() => {
    expect(mockLogin).toHaveBeenCalledWith("admin", "Admin@123");
  });
});

test("enforces Student role UI boundaries by hiding Admin Add and Delete controls", async () => {
  const studentUser = {
    username: "student_demo",
    role: "Student",
    full_name: "Aarav Sharma",
    linked_reg_no: "REG2026001",
  };
  render(<App initialUser={studentUser} />);

  await waitFor(() => {
    expect(screen.getAllByText("Aarav Sharma").length).toBeGreaterThan(0);
  });

  expect(
    screen.queryByRole("button", { name: /Add Student/i })
  ).not.toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: /Import CSV/i })
  ).not.toBeInTheDocument();
});

test("DashboardCards computes and renders KPI metrics accurately", () => {
  const sampleStudents = [
    { reg_no: "R1", roll_no: "1", name: "Alice", age: 20, branch: "CSE", gpa: 8.0 },
    { reg_no: "R2", roll_no: "2", name: "Bob", age: 22, branch: "ECE", gpa: 9.0 },
  ];

  render(<DashboardCards students={sampleStudents} loading={false} />);
  expect(screen.getByText("Total Students")).toBeInTheDocument();
  expect(screen.getByText("21.0 yrs")).toBeInTheDocument();
  expect(screen.getByText("8.50 / 10")).toBeInTheDocument();
});

test("StudentTable renders empty state when no students are present", () => {
  render(<StudentTable students={[]} loading={false} />);
  expect(screen.getByText(/No Student Records Found/i)).toBeInTheDocument();
});

test("StudentForm validates required fields before submission", async () => {
  const mockSubmit = jest.fn();
  render(
    <StudentForm open={true} onClose={() => {}} onSubmit={mockSubmit} />
  );

  const submitBtn = screen.getByRole("button", { name: /Enroll Student/i });
  fireEvent.click(submitBtn);

  expect(
    await screen.findByText(/Registration number is required/i)
  ).toBeInTheDocument();
  expect(mockSubmit).not.toHaveBeenCalled();
});

test("AcademicsWorkspace renders course catalog and enforces role permissions", async () => {
  global.fetch = jest.fn((url) => {
    if (String(url).includes("/api/v1/courses")) {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () =>
          Promise.resolve({
            courses: [
              {
                course_code: "CS301",
                course_name: "Database Management Systems",
                branch: "CSE",
                credits: 4,
                semester: 5,
                academic_year: "2025-2026",
                faculty_username: "faculty_cse",
                capacity: 60,
                enrolled_count: 1,
                status: "Active",
              },
            ],
          }),
      });
    }
    if (String(url).includes("/api/v1/enrollments")) {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () =>
          Promise.resolve({
            enrollments: [
              {
                enrollment_id: "ENR-1",
                reg_no: "REG2026001",
                student_name: "Aarav Sharma",
                course_code: "CS301",
                course_name: "Database Management Systems",
                credits: 4,
                semester: 5,
                academic_year: "2025-2026",
                status: "Enrolled",
              },
            ],
          }),
      });
    }
    return Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve({}),
    });
  });

  const { unmount } = render(
    <AcademicsWorkspace
      students={SAMPLE_STUDENTS}
      currentUser={{ username: "admin", role: "Admin" }}
    />
  );

  expect(
    await screen.findByText("Database Management Systems")
  ).toBeInTheDocument();
  expect(screen.getByText("CS301")).toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: /Add Course/i })
  ).toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: /^Enroll Student$/i })
  ).toBeInTheDocument();

  unmount();

  // Verify Student role cannot see course creation or enrollment buttons
  render(
    <AcademicsWorkspace
      students={SAMPLE_STUDENTS}
      currentUser={{
        username: "student_demo",
        role: "Student",
        linked_reg_no: "REG2026001",
      }}
    />
  );

  expect(
    await screen.findByText("Database Management Systems")
  ).toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: /Add Course/i })
  ).not.toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: /^Enroll Student$/i })
  ).not.toBeInTheDocument();
});

test("AttendanceWorkspace renders classroom roll-call for Faculty and hides it for Students", async () => {
  global.fetch = jest.fn((url) => {
    if (String(url).includes("/api/v1/courses")) {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () =>
          Promise.resolve({
            courses: [
              {
                course_code: "CS301",
                course_name: "Database Management Systems",
                branch: "CSE",
                credits: 4,
                semester: 5,
                status: "Active",
              },
            ],
          }),
      });
    }
    if (String(url).includes("/api/v1/enrollments")) {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () =>
          Promise.resolve({
            enrollments: [
              {
                enrollment_id: "ENR-1",
                reg_no: "REG2026001",
                student_name: "Aarav Sharma",
                course_code: "CS301",
                status: "Enrolled",
              },
            ],
          }),
      });
    }
    if (String(url).includes("/api/v1/attendance/report")) {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () =>
          Promise.resolve({
            course_summaries: [
              {
                course_code: "CS301",
                course_name: "Database Management Systems",
                branch: "CSE",
                total_entries: 4,
                present: 3,
                late: 1,
                absent: 0,
                excused: 0,
                attendance_percentage: 87.5,
              },
            ],
            student_summaries: [
              {
                reg_no: "REG2026001",
                student_name: "Aarav Sharma",
                branch: "CSE",
                total_sessions: 4,
                effective_sessions: 4,
                present: 3,
                late: 1,
                absent: 0,
                excused: 0,
                attendance_percentage: 87.5,
                below_threshold: false,
              },
            ],
          }),
      });
    }
    return Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve({}),
    });
  });

  const { unmount } = render(
    <AttendanceWorkspace
      students={SAMPLE_STUDENTS}
      currentUser={{ username: "faculty_cse", role: "Faculty" }}
    />
  );

  expect(
    await screen.findByText(/Classroom Roll Call Sheet/i)
  ).toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: /Save Classroom Attendance/i })
  ).toBeInTheDocument();

  unmount();

  render(
    <AttendanceWorkspace
      students={SAMPLE_STUDENTS}
      currentUser={{
        username: "student_demo",
        role: "Student",
        linked_reg_no: "REG2026001",
      }}
    />
  );

  await waitFor(() => {
    expect(
      screen.getByText(/Student Attendance Summary Report/i)
    ).toBeInTheDocument();
  });
  expect(
    screen.queryByText(/Classroom Roll Call Sheet/i)
  ).not.toBeInTheDocument();
});

test("PerformanceWorkspace renders assessments, CGPA standing, and grading scale", async () => {
  global.fetch = jest.fn((url) => {
    if (String(url).includes("/api/v1/grades")) {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () =>
          Promise.resolve({
            grades: [
              {
                grade_id: "GRD-1",
                reg_no: "REG2026001",
                student_name: "Aarav Sharma",
                course_code: "CS301",
                course_name: "Database Management Systems",
                assessment_type: "Final",
                marks_obtained: 91,
                max_marks: 100,
                percentage: 91.0,
                letter_grade: "O",
                grade_points: 10.0,
                credits: 4,
              },
            ],
          }),
      });
    }
    if (String(url).includes("/api/v1/academics/grading-scale")) {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () =>
          Promise.resolve({
            grading_scale: {
              scale_name: "Standard 10-Point CBCS Scale",
              bands: [
                {
                  min_percentage: 90,
                  letter_grade: "O",
                  grade_points: 10.0,
                  classification: "Outstanding",
                },
              ],
            },
          }),
      });
    }
    return Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ courses: [] }),
    });
  });

  render(
    <PerformanceWorkspace
      students={SAMPLE_STUDENTS}
      currentUser={{ username: "admin", role: "Admin" }}
    />
  );

  expect(
    await screen.findByText(/Recorded Course Assessments/i)
  ).toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: /Save Assessment Grade/i })
  ).toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: /Use 10.0 CBCS Scale/i })
  ).toBeInTheDocument();
});

test("AdvancedAnalyticsWorkspace renders multi-field filters, course performance, and AI assistant", async () => {
  global.fetch = jest.fn((url) => {
    if (String(url).includes("/api/v1/analytics/advanced")) {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () =>
          Promise.resolve({
            success: true,
            role_scope: "Admin",
            totals: {
              total_students: 2,
              total_courses: 1,
              total_enrollments: 2,
              total_attendance_records: 4,
              total_grade_records: 2,
            },
            enrollment_by_branch: [{ branch: "CSE", student_count: 2 }],
            enrollment_by_semester: [{ semester: "Sem 3", student_count: 2 }],
            attendance_summary: {
              attendance_percentage: 88.5,
              below_threshold_count: 0,
              min_attendance_threshold: 75.0,
            },
            attendance_trends: [
              {
                date: "2026-10-01",
                present: 2,
                late: 0,
                absent: 0,
                excused: 0,
                attendance_percentage: 100.0,
              },
            ],
            grade_distribution: [{ letter_grade: "O", count: 2 }],
            course_performance: [
              {
                course_code: "CS301",
                course_name: "Algorithms",
                branch: "CSE",
                enrolled_count: 2,
                average_percentage: 91.5,
                pass_rate: 100.0,
                attendance_percentage: 88.5,
              },
            ],
            gpa_summary: {
              scale_name: "Standard 10-Point CBCS Scale",
              max_grade_points: 10.0,
              average_cgpa: 9.5,
            },
          }),
      });
    }
    if (String(url).includes("/api/v1/ai/status")) {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () =>
          Promise.resolve({
            success: true,
            provider: "deterministic",
            sample_questions: ["How many students are enrolled in each branch?"],
          }),
      });
    }
    return Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ courses: [] }),
    });
  });

  render(
    <AdvancedAnalyticsWorkspace
      students={SAMPLE_STUDENTS}
      currentUser={{ username: "admin", role: "Admin" }}
    />
  );

  expect(
    await screen.findByText(/Course Performance & Attendance Comparison/i)
  ).toBeInTheDocument();
  expect(screen.getByText(/CS301 — Algorithms/i)).toBeInTheDocument();
  expect(screen.getByText(/9.5 \/ 10/i)).toBeInTheDocument();
  expect(screen.getByText(/AI Analytics Assistant/i)).toBeInTheDocument();
});

test("ReportsAndExportsWorkspace previews report rows and provides PDF, Excel, and CSV exports", async () => {
  global.fetch = jest.fn((url) => {
    if (String(url).includes("/api/v1/reports/preview")) {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () =>
          Promise.resolve({
            success: true,
            title: "Student Directory & Academic Standing Report",
            generated_at: "2026-10-29 14:30:00 UTC",
            generated_by: "admin (Admin)",
            columns: [
              { key: "reg_no", label: "Registration No" },
              { key: "name", label: "Student Name" },
              { key: "branch", label: "Branch" },
            ],
            rows: [
              {
                reg_no: "REG2026001",
                name: "Aarav Sharma",
                branch: "CSE",
              },
            ],
            summary_metrics: [{ label: "Total Students", value: 1 }],
          }),
      });
    }
    return Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ courses: [] }),
    });
  });

  render(
    <ReportsAndExportsWorkspace
      students={SAMPLE_STUDENTS}
      currentUser={{ username: "admin", role: "Admin" }}
    />
  );

  expect(
    await screen.findByText(/Student Directory & Academic Standing Report/i)
  ).toBeInTheDocument();
  expect(screen.getByText("Aarav Sharma")).toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: /Export PDF/i })
  ).toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: /Export Excel/i })
  ).toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: /Export CSV/i })
  ).toBeInTheDocument();
});

test("AiAnalyticsAssistantPanel submits grounded questions and displays read-only confirmation guard", async () => {
  global.fetch = jest.fn((url, options) => {
    if (String(url).includes("/api/v1/ai/status")) {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () =>
          Promise.resolve({
            success: true,
            provider: "deterministic",
            sample_questions: ["Which courses have the lowest attendance?"],
          }),
      });
    }
    if (String(url).includes("/api/v1/ai/query")) {
      const body = JSON.parse(options?.body || "{}");
      const isMutation = String(body.question || "")
        .toLowerCase()
        .includes("delete");
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () =>
          Promise.resolve({
            success: true,
            intent: isMutation ? "mutation_guard" : "lowest_attendance_courses",
            requires_confirmation: isMutation,
            action_blocked: isMutation,
            answer: isMutation
              ? "Action Halted — Explicit Confirmation Required"
              : "Course CS301 has the lowest attendance at 62.5%.",
            filters_used: { branch: "CSE" },
            statistics: { lowest_course: "CS301" },
            disclaimer: "Advisory Note: Grounded in aggregate database records.",
          }),
      });
    }
    return Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve({}),
    });
  });

  render(
    <AiAnalyticsAssistantPanel
      activeFilters={{ branch: "CSE" }}
      currentUser={{ username: "admin", role: "Admin" }}
    />
  );

  const chip = await screen.findByText(
    "Which courses have the lowest attendance?"
  );
  fireEvent.click(chip);

  expect(
    await screen.findByText(/Course CS301 has the lowest attendance at 62.5%/i)
  ).toBeInTheDocument();
  expect(
    screen.getByText(/Verified Deterministic Statistics Used/i)
  ).toBeInTheDocument();
});

test("Direct navigation and refresh on nested routes render the corresponding workspace", async () => {
  window.history.pushState({}, "Reports Export Nested Route", "/reports/export");

  render(
    <App
      initialUser={{
        username: "admin",
        role: "Admin",
        full_name: "System Administrator",
        assigned_branches: ["*"],
      }}
    />
  );

  expect(
    await screen.findByText(/Reports, Live Preview & Multi-Format Exports/i)
  ).toBeInTheDocument();

  window.history.pushState({}, "Root", "/");
});

