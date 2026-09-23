import re


SECTION_ALIASES = {
    "summary": [
        "summary",
        "professional summary",
        "profile summary",
        "career objective",
        "objective",
        "about me",
    ],

    "education": [
        "education",
        "academic qualification",
        "academic qualifications",
        "academic background",
    ],

    "skills": [
        "skills",
        "technical skills",
        "core skills",
        "key skills",
        "technologies",
        "tech stack",
    ],

    "projects": [
        "projects",
        "personal projects",
        "academic projects",
        "project experience",
    ],

    "experience": [
        "experience",
        "work experience",
        "professional experience",
        "employment",
        "internship",
        "internships",
    ],

    "certifications": [
        "certifications",
        "certificates",
        "courses and certifications",
        "licenses and certifications",
    ],

    "achievements": [
        "achievements",
        "awards",
        "honors",
        "accomplishments",
    ],
}


def detect_sections(text: str) -> dict:
    normalized_text = text.lower()

    detected = {}

    for section, aliases in SECTION_ALIASES.items():
        found = False

        for alias in aliases:
            pattern = rf"(?im)^\s*{re.escape(alias)}\s*:?\s*$"

            if re.search(pattern, normalized_text):
                found = True
                break

        detected[section] = found

    detected["contact"] = detect_contact_details(text)

    return detected


def detect_contact_details(text: str) -> bool:
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

    linkedin_found = "linkedin.com" in text.lower()
    github_found = "github.com" in text.lower()

    return any(
        [
            email_found,
            phone_found,
            linkedin_found,
            github_found,
        ]
    )