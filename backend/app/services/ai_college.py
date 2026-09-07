import json

from app.core.config import settings


def generate_college_response(
    college_context: dict,
    user_message: str,
    conversation_history=None,
):
    text = user_message.lower().strip()

    college = college_context.get("college") or {}
    departments = college_context.get("departments") or []
    summary = college_context.get("summary") or {}
    student_skills = college_context.get("student_skills") or []
    industry_demand = college_context.get("industry_demand") or []
    skill_gap = college_context.get("skill_gap") or []
    collaborations = college_context.get("collaborations") or []

    # =====================================================
    # MY COLLEGE
    # =====================================================

    if (
        "my college" in text
        or "college profile" in text
    ):
        return (
            f"College: {college.get('name')}\n"
            f"University: {college.get('university') or 'Not added'}\n"
            f"City: {college.get('city') or 'Not added'}\n"
            f"State: {college.get('state') or 'Not added'}\n"
            f"Verified: {'Yes' if college.get('is_verified') else 'No'}"
        )

    # =====================================================
    # DEPARTMENTS
    # =====================================================

    if "department" in text:
        if not departments:
            return "No departments have been added yet."

        lines = []

        for row in departments:
            name = row.get("name", "Department")
            code = row.get("code")

            if code:
                lines.append(
                    f"• {name} ({code})"
                )
            else:
                lines.append(
                    f"• {name}"
                )

        return (
            "Your college departments:\n\n"
            + "\n".join(lines)
        )

    # =====================================================
    # COLLEGE SUMMARY
    # =====================================================

    if (
        "summary" in text
        or "dashboard" in text
        or "overview" in text
        or "placement status" in text
    ):
        return (
            "College Overview:\n\n"
            f"Total Students: {summary.get('total_students', 0)}\n"
            f"Skills Recorded: {summary.get('total_skills', 0)}\n"
            f"Applications: {summary.get('applications', 0)}\n"
            f"Shortlisted: {summary.get('shortlisted', 0)}\n"
            f"Interviews: {summary.get('interviews', 0)}\n"
            f"Selected: {summary.get('selected', 0)}"
        )

    # =====================================================
    # TOP STUDENT SKILLS
    # =====================================================

    if (
        "student skills" in text
        or "top skills" in text
        or "skill overview" in text
        or "skills overview" in text
    ):
        if not student_skills:
            return (
                "No student skill data is available yet."
            )

        lines = [
            f"{index + 1}. "
            f"{row['skill']} — "
            f"{row['students']} students"
            for index, row
            in enumerate(student_skills[:10])
        ]

        return (
            "Top student skills:\n\n"
            + "\n".join(lines)
        )

    # =====================================================
    # INDUSTRY DEMAND
    # =====================================================

    if (
        "industry demand" in text
        or "demanded skills" in text
        or "companies demanding" in text
        or "companies need" in text
    ):
        if not industry_demand:
            return (
                "No industry demand data is available yet."
            )

        lines = [
            f"{index + 1}. "
            f"{row['skill']} — "
            f"{row['demand']} opportunities"
            for index, row
            in enumerate(industry_demand[:10])
        ]

        return (
            "Current industry skill demand:\n\n"
            + "\n".join(lines)
        )

    # =====================================================
    # SKILL GAP
    # =====================================================

    if (
        "skill gap" in text
        or "missing skills" in text
        or "students missing" in text
        or "training need" in text
    ):
        positive_gaps = [
            row
            for row in skill_gap
            if row.get(
                "gap_percentage",
                0
            ) > 0
        ]

        if not positive_gaps:
            return (
                "No major positive skill gap was detected "
                "from the current available data."
            )

        lines = [
            f"{index + 1}. "
            f"{row['skill']} — "
            f"Gap {row['gap_percentage']}% "
            f"({row['severity']})"
            for index, row
            in enumerate(positive_gaps[:10])
        ]

        return (
            "Priority student skill gaps:\n\n"
            + "\n".join(lines)
        )

    # =====================================================
    # COLLABORATIONS
    # =====================================================

    if "collaboration" in text:
        if not collaborations:
            return (
                "Your college currently has no "
                "collaboration requests."
            )

        lines = []

        for row in collaborations[:10]:
            lines.append(
                f"• {row['title']} — "
                f"{row['type']} — "
                f"{row['status']}"
            )

        return (
            "Your college collaborations:\n\n"
            + "\n".join(lines)
        )

    # =====================================================
    # TRAINING / WORKSHOP RECOMMENDATION
    # =====================================================

    if (
        "training" in text
        or "workshop" in text
        or "what should we teach" in text
        or "what should students learn" in text
    ):
        positive_gaps = [
            row
            for row in skill_gap
            if row.get(
                "gap_percentage",
                0
            ) > 0
        ]

        if not positive_gaps:
            return (
                "Current data does not show a major "
                "skill gap for recommending training."
            )

        top_gaps = positive_gaps[:5]

        lines = [
            f"{index + 1}. "
            f"{row['skill']} — "
            f"{row['severity']} priority"
            for index, row
            in enumerate(top_gaps)
        ]

        return (
            "Based on current skill-gap data, "
            "your college should prioritize training in:\n\n"
            + "\n".join(lines)
        )

    # =====================================================
    # NO OPENAI KEY
    # =====================================================

    if not settings.OPENAI_API_KEY:
        return (
            "I can help with your college's real SkillBridge data.\n\n"
            "You can ask:\n"
            "• Show my college\n"
            "• Show departments\n"
            "• Show college overview\n"
            "• Show top student skills\n"
            "• What skills are companies demanding?\n"
            "• Show our skill gaps\n"
            "• What training should we organize?\n"
            "• Show collaborations"
        )

    # =====================================================
    # OPENAI
    # =====================================================

    from openai import OpenAI

    client = OpenAI(
        api_key=settings.OPENAI_API_KEY
    )

    context_json = json.dumps(
        college_context,
        default=str
    )

    history = "\n".join(
        f"{message['role']}: {message['content']}"
        for message
        in (conversation_history or [])[-10:]
    )

    response = client.responses.create(
        model=settings.OPENAI_MODEL,

        instructions="""
You are the SkillBridge AI College Intelligence Assistant.

You help the currently logged-in College/TPO understand
its own college data and improve student career outcomes.

You may analyze:
- college profile
- departments
- student skill analytics
- applications
- shortlisting
- interviews
- selections
- industry skill demand
- skill-gap analytics
- training needs
- workshops
- industry collaborations
- internship and placement readiness

STRICT RULES:

1. Use only the supplied COLLEGE CONTEXT.
2. Never invent numbers, students, skills, companies or collaborations.
3. Only discuss data belonging to the logged-in college.
4. Never reveal another college's private data.
5. Do not expose sensitive individual student information.
6. Prefer aggregate student analytics.
7. Clearly say when requested data is unavailable.
8. Recommendations must be based on actual skill-gap and industry-demand data.
9. Keep answers concise, practical and easy to understand.
10. Help the college improve internship and placement readiness.
""",

        input=f"""
COLLEGE CONTEXT:
{context_json}

RECENT CONVERSATION:
{history}

QUESTION:
{user_message}
"""
    )

    return response.output_text