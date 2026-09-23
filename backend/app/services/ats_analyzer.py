import re


def calculate_ats_score(
    text: str,
    sections: dict,
    skills: list[dict],
) -> dict:

    score = 0
    breakdown = {}
    issues = []
    strengths = []

    # -----------------------------------------
    # 1. Contact Information - 10 marks
    # -----------------------------------------

    email_found = bool(
        re.search(
            r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
            text,
        )
    )

    phone_found = bool(
        re.search(
            r"(?:\+91[\s-]?)?[6-9]\d{9}",
            text,
        )
    )

    contact_score = 0

    if email_found:
        contact_score += 5

    if phone_found:
        contact_score += 5

    breakdown["contact"] = {
        "score": contact_score,
        "max_score": 10,
    }

    score += contact_score

    if contact_score == 10:
        strengths.append("Contact information is complete.")
    else:
        issues.append("Add valid email and phone number.")


    # -----------------------------------------
    # 2. Education - 10 marks
    # -----------------------------------------

    education_score = (
        10
        if sections.get("education")
        else 0
    )

    breakdown["education"] = {
        "score": education_score,
        "max_score": 10,
    }

    score += education_score

    if education_score:
        strengths.append("Education section found.")
    else:
        issues.append("Education section is missing.")


    # -----------------------------------------
    # 3. Skills - 20 marks
    # -----------------------------------------

    skill_count = len(skills)

    if skill_count >= 8:
        skills_score = 20

    elif skill_count >= 5:
        skills_score = 15

    elif skill_count >= 3:
        skills_score = 10

    elif skill_count >= 1:
        skills_score = 5

    else:
        skills_score = 0

    breakdown["skills"] = {
        "score": skills_score,
        "max_score": 20,
        "detected_count": skill_count,
    }

    score += skills_score

    if skill_count >= 5:
        strengths.append(
            f"{skill_count} technical skills detected."
        )
    else:
        issues.append(
            "Add more relevant technical skills."
        )


    # -----------------------------------------
    # 4. Projects - 20 marks
    # -----------------------------------------

    projects_score = (
        20
        if sections.get("projects")
        else 0
    )

    breakdown["projects"] = {
        "score": projects_score,
        "max_score": 20,
    }

    score += projects_score

    if projects_score:
        strengths.append("Projects section found.")
    else:
        issues.append(
            "Add projects that demonstrate your skills."
        )


    # -----------------------------------------
    # 5. Experience - 15 marks
    # -----------------------------------------

    experience_score = (
        15
        if sections.get("experience")
        else 0
    )

    breakdown["experience"] = {
        "score": experience_score,
        "max_score": 15,
    }

    score += experience_score

    if experience_score:
        strengths.append(
            "Experience / internship section found."
        )
    else:
        issues.append(
            "Experience or internship section is missing."
        )


    # -----------------------------------------
    # 6. Certifications - 10 marks
    # -----------------------------------------

    certification_score = (
        10
        if sections.get("certifications")
        else 0
    )

    breakdown["certifications"] = {
        "score": certification_score,
        "max_score": 10,
    }

    score += certification_score

    if certification_score:
        strengths.append(
            "Certifications section found."
        )
    else:
        issues.append(
            "Relevant certifications can strengthen the resume."
        )


    # -----------------------------------------
    # 7. Summary - 5 marks
    # -----------------------------------------

    summary_score = (
        5
        if sections.get("summary")
        else 0
    )

    breakdown["summary"] = {
        "score": summary_score,
        "max_score": 5,
    }

    score += summary_score

    if not summary_score:
        issues.append(
            "Add a concise professional summary."
        )


    # -----------------------------------------
    # 8. Links - 5 marks
    # -----------------------------------------

    lower_text = text.lower()

    github_found = (
        "github.com" in lower_text
    )

    linkedin_found = (
        "linkedin.com" in lower_text
    )

    links_score = 0

    if github_found:
        links_score += 3

    if linkedin_found:
        links_score += 2

    breakdown["professional_links"] = {
        "score": links_score,
        "max_score": 5,
    }

    score += links_score

    if not github_found:
        issues.append(
            "Add your GitHub profile."
        )

    if not linkedin_found:
        issues.append(
            "Add your LinkedIn profile."
        )


    # -----------------------------------------
    # 9. Achievements - 5 marks
    # -----------------------------------------

    achievements_score = (
        5
        if sections.get("achievements")
        else 0
    )

    breakdown["achievements"] = {
        "score": achievements_score,
        "max_score": 5,
    }

    score += achievements_score


    # -----------------------------------------
    # Final
    # -----------------------------------------

    final_score = min(score, 100)

    return {
        "score": final_score,
        "max_score": 100,
        "breakdown": breakdown,
        "strengths": strengths,
        "issues": issues,
    }