import json
import os
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone

from logs.logger import logger
from services.academic_service import (
    can_manage_course,
    get_course,
    is_student_enrolled,
)
from services.report_service import (
    compute_advanced_analytics,
    validate_and_normalize_filters,
)
from services.student_service import search_student

# Allowlisted read-only analytical intents (never executes arbitrary queries/code)
ALLOWED_INTENTS = (
    "branch_enrollment",
    "lowest_attendance_courses",
    "semester_attendance",
    "course_performance",
    "trends_summary",
    "report_narrative",
    "general_overview",
)

MUTATION_KEYWORDS_REGEX = re.compile(
    r"\b(delete|remove|drop|erase|wipe|update|modify|edit|change|insert|create|add|enroll|unenroll|archive|reset|grant|revoke)\b",
    re.IGNORECASE,
)

REG_NO_TOKEN_REGEX = re.compile(r"\b(REG[A-Za-z0-9_-]{3,20})\b", re.IGNORECASE)
COURSE_TOKEN_REGEX = re.compile(r"\b([A-Z]{2,5}\d{2,4})\b", re.IGNORECASE)
SEMESTER_TOKEN_REGEX = re.compile(
    r"\b(?:semester|sem)\s*([1-8])\b", re.IGNORECASE
)
BRANCH_TOKENS = {"CSE", "ECE", "ME", "CE", "EE", "IT", "AIML", "DS"}

ADVISORY_DISCLAIMER = (
    "Advisory Note: AI-generated insights are suggestions grounded in aggregate "
    "database records and do not constitute verified academic diagnoses or automated decisions."
)

# Optional hook for unit testing external LLM provider behavior (rate limit, timeout, malformed JSON)
_custom_llm_caller = None


def set_custom_llm_caller(caller_fn):
    """Set or clear a custom external LLM caller function for isolated testing."""
    global _custom_llm_caller
    _custom_llm_caller = caller_fn


def get_ai_assistant_status():
    """Return non-sensitive AI assistant configuration metadata."""
    provider = (
        os.environ.get("AI_ASSISTANT_PROVIDER", "deterministic").strip().lower()
        or "deterministic"
    )
    model = (
        os.environ.get("AI_ASSISTANT_MODEL", "gemini-2.5-flash").strip()
        or "gemini-2.5-flash"
    )
    has_key = bool(os.environ.get("AI_ASSISTANT_API_KEY", "").strip())

    return {
        "success": True,
        "enabled": True,
        "provider": provider,
        "model": model if provider != "deterministic" else "deterministic-engine-v1",
        "api_key_configured": has_key,
        "requires_api_key_for_core": False,
        "privacy_mode": "aggregate_only_no_pii",
        "allowed_intents": list(ALLOWED_INTENTS),
        "sample_questions": [
            "How many students are enrolled in each branch?",
            "Which courses have the lowest attendance?",
            "What is the average attendance for Semester 3?",
            "Summarize the academic performance of course CS301.",
            "Explain recent enrollment and attendance trends.",
            "Generate a concise narrative for the current filtered report.",
        ],
        "disclaimer": ADVISORY_DISCLAIMER,
    }


def _classify_intent(question):
    q = str(question or "").strip().lower()
    if any(
        w in q
        for w in (
            "lowest attendance",
            "low attendance",
            "worst attendance",
            "shortage",
            "below 75",
        )
    ):
        return "lowest_attendance_courses"
    if ("average attendance" in q or "attendance" in q) and (
        "semester" in q or "sem " in q
    ):
        return "semester_attendance"
    if any(
        w in q
        for w in (
            "performance",
            "grade",
            "gpa",
            "cgpa",
            "marks",
            "pass rate",
            "summarize the academic",
        )
    ):
        return "course_performance"
    if any(w in q for w in ("trend", "recent", "over time", "chronological")):
        return "trends_summary"
    if any(w in q for w in ("narrative", "report", "executive summary")):
        return "report_narrative"
    if any(
        w in q
        for w in ("how many students", "each branch", "branch", "department", "enrolled")
    ):
        return "branch_enrollment"
    return "general_overview"


def _extract_prompt_entities(question):
    """Extract explicit reg_no, course_code, branch, or semester mentions from the natural-language prompt."""
    text = str(question or "")
    entities = {}

    reg_match = REG_NO_TOKEN_REGEX.search(text)
    if reg_match:
        entities["reg_no"] = reg_match.group(1).upper()

    sem_match = SEMESTER_TOKEN_REGEX.search(text)
    if sem_match:
        entities["semester"] = sem_match.group(1)

    upper_words = re.findall(r"\b[A-Za-z0-9_-]+\b", text.upper())
    for w in upper_words:
        if w in BRANCH_TOKENS:
            entities["branch"] = w
            break

    for match in COURSE_TOKEN_REGEX.finditer(text):
        token = match.group(1).upper()
        if not token.startswith("REG") and token not in BRANCH_TOKENS:
            if get_course(token) is not None or re.match(r"^[A-Z]{2,4}\d{3}$", token):
                entities["course_code"] = token
                break

    return entities


def _build_anonymized_aggregate_context(analytics):
    """
    Build a strictly anonymized aggregate dictionary safe for external AI providers.
    Never includes student names, registration numbers, emails, or phone numbers.
    """
    return {
        "applied_filters": {
            k: v
            for k, v in (analytics.get("applied_filters") or {}).items()
            if k != "reg_no"
        },
        "totals": analytics.get("totals", {}),
        "enrollment_by_branch": analytics.get("enrollment_by_branch", []),
        "enrollment_by_semester": analytics.get("enrollment_by_semester", []),
        "enrollment_by_academic_year": analytics.get(
            "enrollment_by_academic_year", []
        ),
        "attendance_summary": analytics.get("attendance_summary", {}),
        "attendance_trends": analytics.get("attendance_trends", [])[-14:],
        "grade_distribution": analytics.get("grade_distribution", []),
        "course_performance": analytics.get("course_performance", []),
        "gpa_summary": analytics.get("gpa_summary", {}),
    }


def _build_deterministic_answer(intent, analytics, question=""):
    """
    Produce a deterministic, database-grounded markdown response using ONLY verified figures.
    Never invents statistics when records are missing.
    """
    af = analytics.get("applied_filters") or {}
    totals = analytics.get("totals") or {}
    filter_parts = [
        f"{k}={v}"
        for k, v in af.items()
        if v and v != "All"
    ]
    filter_desc = ", ".join(filter_parts) if filter_parts else "All permitted records"

    total_students = totals.get("total_students", 0)
    total_courses = totals.get("total_courses", 0)
    att_sum = analytics.get("attendance_summary") or {}
    gpa_sum = analytics.get("gpa_summary") or {}
    branches = analytics.get("enrollment_by_branch") or []
    courses_perf = analytics.get("course_performance") or []
    trends = analytics.get("attendance_trends") or []

    if (
        total_students == 0
        and total_courses == 0
        and totals.get("total_attendance_records", 0) == 0
        and totals.get("total_grade_records", 0) == 0
    ):
        return {
            "narrative": (
                f"No matching records were found in the database for the active filters ({filter_desc}). "
                "No statistics were generated because no underlying student, course, attendance, or grade records exist for this selection."
            ),
            "statistics": {
                "total_students": 0,
                "total_courses": 0,
                "filters_applied": filter_desc,
            },
            "suggestions": [
                "Broaden the branch, semester, or date-range filters to include active cohorts.",
            ],
        }

    if intent == "branch_enrollment":
        if not branches:
            narrative = f"No students are currently enrolled matching the active filters ({filter_desc})."
        else:
            breakdown = ", ".join(
                f"**{b['branch']}**: {b['student_count']} student(s)"
                + (f" (Avg CGPA: {b['avg_gpa']})" if b.get("avg_gpa") is not None else "")
                for b in branches
            )
            narrative = (
                f"Across **{total_students}** total student(s) ({filter_desc}), "
                f"branch-wise enrollment is distributed as follows: {breakdown}."
            )
        return {
            "narrative": narrative,
            "statistics": {
                "total_students": total_students,
                "enrollment_by_branch": branches,
            },
            "suggestions": [
                "Review course capacity utilization for high-enrollment branches.",
            ],
        }

    if intent == "lowest_attendance_courses":
        with_att = [
            c for c in courses_perf if c.get("attendance_percentage") is not None
        ]
        if not with_att:
            narrative = (
                f"No course attendance sessions have been recorded yet for the active filters ({filter_desc})."
            )
            ranked = []
        else:
            ranked = sorted(with_att, key=lambda x: x["attendance_percentage"])
            lowest = ranked[:3]
            items_txt = ", ".join(
                f"**{c['course_code']} ({c['course_name']})** at **{c['attendance_percentage']}%** ({c['total_attendance_entries']} session entries)"
                for c in lowest
            )
            narrative = (
                f"Based on recorded classroom sessions ({filter_desc}), the course(s) with the lowest attendance are: "
                f"{items_txt}. Minimum institutional threshold is **{att_sum.get('min_attendance_threshold', 75.0)}%**."
            )
        return {
            "narrative": narrative,
            "statistics": {
                "lowest_attendance_courses": ranked[:5],
                "overall_attendance_percentage": att_sum.get(
                    "attendance_percentage", 0.0
                ),
                "below_threshold_students": att_sum.get(
                    "below_threshold_count", 0
                ),
            },
            "suggestions": [
                "Consider scheduling academic advising or remedial sessions for courses below the 75% attendance threshold.",
            ],
        }

    if intent == "semester_attendance":
        sem_label = af.get("semester", "All")
        total_sess = att_sum.get("total_sessions", 0)
        if total_sess == 0:
            # Check student profile attendance_pct fallback if available
            branch_atts = [
                b["avg_attendance"]
                for b in branches
                if b.get("avg_attendance") is not None
            ]
            if branch_atts:
                avg_profile_att = round(sum(branch_atts) / len(branch_atts), 2)
                narrative = (
                    f"For Semester **{sem_label}** ({filter_desc}), no individual classroom session logs were found, "
                    f"but student profile records show an average attendance of **{avg_profile_att}%** across **{total_students}** student(s)."
                )
            else:
                narrative = (
                    f"No attendance records were found for Semester **{sem_label}** ({filter_desc})."
                )
        else:
            narrative = (
                f"For Semester **{sem_label}** ({filter_desc}), the aggregate attendance percentage is "
                f"**{att_sum['attendance_percentage']}%** across **{total_sess}** recorded session entries "
                f"(Present: {att_sum['present']}, Late: {att_sum['late']}, Absent: {att_sum['absent']}, Excused: {att_sum['excused']}). "
                f"Currently, **{att_sum['below_threshold_count']}** student(s) are below the {att_sum['min_attendance_threshold']}% threshold."
            )
        return {
            "narrative": narrative,
            "statistics": {
                "semester": sem_label,
                "attendance_summary": att_sum,
            },
            "suggestions": [
                "Monitor students with attendance below 75% early in the semester.",
            ],
        }

    if intent == "course_performance":
        if not courses_perf:
            narrative = (
                f"No course performance or grade records are available for the active filters ({filter_desc})."
            )
        else:
            parts = []
            for c in courses_perf[:5]:
                avg_str = (
                    f"{c['average_percentage']}%"
                    if c.get("average_percentage") is not None
                    else "No grades yet"
                )
                pass_str = (
                    f"{c['pass_rate']}% pass rate"
                    if c.get("pass_rate") is not None
                    else "N/A"
                )
                att_str = (
                    f"{c['attendance_percentage']}% attendance"
                    if c.get("attendance_percentage") is not None
                    else "No attendance logged"
                )
                parts.append(
                    f"**{c['course_code']} ({c['course_name']})**: Avg Marks {avg_str}, {pass_str}, {att_str} ({c['enrolled_count']} enrolled)"
                )
            cgpa_txt = (
                f"Cohort Credit-Weighted Average CGPA is **{gpa_sum['average_cgpa']} / {gpa_sum['max_grade_points']}**."
                if gpa_sum.get("average_cgpa") is not None
                else "No credit-weighted CGPA has been computed yet."
            )
            narrative = (
                f"Academic performance summary ({filter_desc}): "
                + "; ".join(parts)
                + f". {cgpa_txt}"
            )
        return {
            "narrative": narrative,
            "statistics": {
                "course_performance": courses_perf,
                "gpa_summary": gpa_sum,
                "grade_distribution": analytics.get("grade_distribution", []),
            },
            "suggestions": [
                "Review assessment distributions for courses with pass rates below 80%.",
            ],
        }

    if intent == "trends_summary":
        sem_breakdown = ", ".join(
            f"{s['semester']}: {s['student_count']}"
            for s in (analytics.get("enrollment_by_semester") or [])
        )
        if trends:
            first_t = trends[0]
            last_t = trends[-1]
            delta = round(
                last_t["attendance_percentage"] - first_t["attendance_percentage"],
                2,
            )
            direction = (
                f"increased by {delta}%"
                if delta > 0
                else (f"decreased by {abs(delta)}%" if delta < 0 else "remained stable")
            )
            att_trend_txt = (
                f"Across **{len(trends)}** recorded session date(s) from **{first_t['date']}** ({first_t['attendance_percentage']}%) "
                f"to **{last_t['date']}** ({last_t['attendance_percentage']}%), attendance has {direction}."
            )
        else:
            att_trend_txt = "No dated attendance sessions have been logged in the selected date window."

        narrative = (
            f"Enrollment & Attendance Trends ({filter_desc}): Total active students: **{total_students}** "
            f"(Semester distribution: {sem_breakdown or 'N/A'}). {att_trend_txt}"
        )
        return {
            "narrative": narrative,
            "statistics": {
                "enrollment_by_semester": analytics.get(
                    "enrollment_by_semester", []
                ),
                "enrollment_by_academic_year": analytics.get(
                    "enrollment_by_academic_year", []
                ),
                "attendance_trends": trends,
            },
            "suggestions": [
                "Use date-range filters to compare attendance before and after midterm assessments.",
            ],
        }

    # Default: report_narrative / general_overview
    branch_summary = ", ".join(
        f"{b['branch']} ({b['student_count']})" for b in branches
    )
    avg_cgpa = (
        f"{gpa_sum['average_cgpa']} / {gpa_sum['max_grade_points']}"
        if gpa_sum.get("average_cgpa") is not None
        else "N/A"
    )
    narrative = (
        f"**Executive Report Narrative ({filter_desc})**: The dataset covers **{total_students}** student(s) "
        f"across **{ len(branches) }** branch(es) ({branch_summary or 'None'}) and **{total_courses}** active course(s). "
        f"Aggregate session attendance stands at **{att_sum.get('attendance_percentage', 0.0)}%** "
        f"({att_sum.get('below_threshold_count', 0)} student(s) below the {att_sum.get('min_attendance_threshold', 75.0)}% threshold), "
        f"and the credit-weighted cohort CGPA is **{avg_cgpa}**."
    )
    return {
        "narrative": narrative,
        "statistics": {
            "totals": totals,
            "enrollment_by_branch": branches,
            "attendance_summary": att_sum,
            "gpa_summary": gpa_sum,
        },
        "suggestions": [
            "Export this filtered view to PDF or Excel for departmental review.",
        ],
    }


def _invoke_external_llm(provider, question, anonymized_context, deterministic_draft):
    """
    Call external LLM provider (Gemini or OpenAI) using backend-only credentials,
    strictly passing anonymized aggregate statistics (no student PII).
    """
    if _custom_llm_caller is not None:
        return _custom_llm_caller(
            provider=provider,
            question=question,
            context=anonymized_context,
            draft=deterministic_draft,
        )

    api_key = os.environ.get("AI_ASSISTANT_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            f"AI provider '{provider}' is selected, but AI_ASSISTANT_API_KEY is not configured on the server."
        )

    timeout_sec = float(os.environ.get("AI_ASSISTANT_TIMEOUT_SEC", 8))
    model = os.environ.get("AI_ASSISTANT_MODEL", "").strip()

    system_instruction = (
        "You are a read-only Academic Analytics Assistant. Answer the user's question "
        "ONLY using the verified deterministic statistics provided in JSON. "
        "Never invent numbers, never speculate beyond the dataset, and always mention "
        "the active filters. Keep the response concise (2-4 sentences)."
    )
    user_prompt = (
        f"User Question: {question}\n\n"
        f"Verified Deterministic Draft: {deterministic_draft}\n\n"
        f"Anonymized Aggregate Statistics JSON:\n{json.dumps(anonymized_context)}"
    )

    if provider == "gemini":
        model_name = model or "gemini-2.5-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": f"{system_instruction}\n\n{user_prompt}"}],
                }
            ],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 350},
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            raw_body = resp.read().decode("utf-8")
            parsed = json.loads(raw_body)
            candidates = parsed.get("candidates") or []
            text = (
                candidates[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "")
                .strip()
            )
            if not text:
                raise ValueError("Empty response from Gemini provider")
            return text

    if provider == "openai":
        model_name = model or "gpt-4o-mini"
        url = "https://api.openai.com/v1/chat/completions"
        payload = {
            "model": model_name,
            "temperature": 0.1,
            "max_tokens": 350,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_prompt},
            ],
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            raw_body = resp.read().decode("utf-8")
            parsed = json.loads(raw_body)
            choices = parsed.get("choices") or []
            text = choices[0].get("message", {}).get("content", "").strip()
            if not text:
                raise ValueError("Empty response from OpenAI provider")
            return text

    raise ValueError(f"Unsupported AI provider '{provider}'")


def answer_analytics_question(user, question, raw_filters=None):
    """
    Main entry point for Objective C (AI Analytics Assistant):
      1. Validates authentication and non-empty question.
      2. Blocks any data-modifying request and requires explicit confirmation via standard UI forms.
      3. Extracts prompt entities (branch, course, semester, reg_no) and enforces RBAC boundaries.
      4. Computes deterministic database statistics via allowlisted service functions.
      5. Optionally formats the narrative via configured backend LLM (without sending PII).
    """
    if not user or not isinstance(user, dict):
        return {"error": "Authentication required", "status_code": 401}

    q_text = str(question or "").strip()
    if not q_text:
        return {"error": "Please provide a question for the analytics assistant", "status_code": 400}
    if len(q_text) > 600:
        return {"error": "Question is too long (maximum 600 characters)", "status_code": 400}

    # Requirement 13: Require explicit confirmation / block any action that modifies data
    if MUTATION_KEYWORDS_REGEX.search(q_text):
        return {
            "success": True,
            "intent": "mutation_guard",
            "requires_confirmation": True,
            "action_blocked": True,
            "answer": (
                "Action Halted — Explicit Confirmation Required: The AI Analytics Assistant is strictly "
                "read-only and never modifies student, course, attendance, or grade records automatically. "
                "To perform any create, update, archive, or delete operation, please use the authorized "
                "management forms and confirm the action explicitly."
            ),
            "filters_used": raw_filters or {},
            "statistics": {},
            "suggestions": [],
            "disclaimer": ADVISORY_DISCLAIMER,
        }

    # Merge explicit UI filters with any entities mentioned in the natural-language question
    merged_filters = dict(raw_filters or {})
    prompt_entities = _extract_prompt_entities(q_text)
    for key in ("branch", "course_code", "semester", "reg_no"):
        if key in prompt_entities and not merged_filters.get(key):
            merged_filters[key] = prompt_entities[key]

    # Additional Student RBAC guard on natural-language questions:
    # Students can only ask about their own linked record and enrolled courses
    if user.get("role") == "Student":
        linked_reg = str(user.get("linked_reg_no") or "").strip()
        if (
            prompt_entities.get("reg_no")
            and prompt_entities["reg_no"].upper() != linked_reg.upper()
        ):
            return {
                "error": "Access denied: Students may only query analytics for their own registration number",
                "status_code": 403,
            }
        own_student = search_student(linked_reg) or {}
        own_branch = str(own_student.get("branch") or "").strip().upper()
        if (
            prompt_entities.get("branch")
            and own_branch
            and prompt_entities["branch"].upper() != own_branch
        ):
            return {
                "error": f"Access denied: Students cannot query analytics for branch '{prompt_entities['branch']}'",
                "status_code": 403,
            }
        target_course = merged_filters.get("course_code")
        if target_course and not is_student_enrolled(linked_reg, target_course):
            return {
                "error": f"Access denied: Student is not enrolled in course '{target_course}'",
                "status_code": 403,
            }
        merged_filters["reg_no"] = linked_reg

    # Validate filters and compute RBAC-scoped deterministic analytics
    analytics = compute_advanced_analytics(user, merged_filters)
    if "error" in analytics:
        return analytics

    intent = _classify_intent(q_text)
    det = _build_deterministic_answer(intent, analytics, question=q_text)
    narrative = det["narrative"]

    provider = (
        os.environ.get("AI_ASSISTANT_PROVIDER", "deterministic").strip().lower()
        or "deterministic"
    )

    if provider != "deterministic":
        anonymized_ctx = _build_anonymized_aggregate_context(analytics)
        try:
            narrative = _invoke_external_llm(
                provider=provider,
                question=q_text,
                anonymized_context=anonymized_ctx,
                deterministic_draft=det["narrative"],
            )
        except urllib.error.HTTPError as http_err:
            logger.warning(
                f"AI provider HTTP error (status {http_err.code}) for user {user.get('username')}"
            )
            if http_err.code == 429:
                return {
                    "error": "AI assistant provider is currently rate-limited. Please retry shortly.",
                    "status_code": 429,
                }
            return {
                "error": "AI assistant provider is temporarily unavailable.",
                "status_code": 503,
            }
        except RuntimeError as cfg_err:
            logger.warning(f"AI provider configuration error: {cfg_err}")
            return {
                "error": str(cfg_err),
                "status_code": 503,
            }
        except Exception as exc:
            logger.warning(f"AI provider call failed: {type(exc).__name__}")
            return {
                "error": "AI assistant provider encountered an unexpected response or timeout.",
                "status_code": 503,
            }

    return {
        "success": True,
        "provider": provider,
        "intent": intent,
        "question": q_text,
        "answer": narrative,
        "requires_confirmation": False,
        "action_blocked": False,
        "filters_used": analytics["applied_filters"],
        "role_scope": analytics["role_scope"],
        "statistics": det["statistics"],
        "suggestions": det["suggestions"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "disclaimer": ADVISORY_DISCLAIMER,
    }
