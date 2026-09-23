import json
import os
from typing import Any

from openai import OpenAI


MODEL_NAME = os.getenv(
    "OPENAI_MODEL",
    "gpt-5.6-luna",
)

MAX_RESUME_CHARS = 15000


def get_openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not configured"
        )

    return OpenAI(
        api_key=api_key,
        timeout=45.0,
        max_retries=2,
    )


def clean_resume_text(
    resume_text: str,
) -> str:

    text = " ".join(
        resume_text.split()
    )

    return text[:MAX_RESUME_CHARS]


def generate_resume_guidance(
    resume_text: str,
    ats_result: dict,
    detected_skills: list[dict],
    target_role: str | None = None,
    match_result: dict | None = None,
) -> dict[str, Any]:

    client = get_openai_client()

    clean_text = clean_resume_text(
        resume_text
    )

    skills = [
        skill.get("name")
        for skill in detected_skills
        if skill.get("name")
    ]

    context = {
        "target_role": target_role,
        "ats_analysis": ats_result,
        "detected_skills": skills,
        "opportunity_match": (
            match_result or {}
        ),
    }

    instructions = """
You are the resume improvement layer of SkillBridge AI.

The backend has already performed deterministic resume parsing,
skill detection, ATS readiness scoring, and opportunity matching.

IMPORTANT RULES:

1. Never calculate or change ATS scores.
2. Never calculate or change opportunity match percentages.
3. Never claim a skill is verified.
4. Never invent experience.
5. Never invent projects.
6. Never invent certifications.
7. Never invent companies or internships.
8. Never invent achievements.
9. Never invent numerical metrics.
10. Only use information actually present in the supplied resume
    and analysis context.
11. If information is unavailable, do not guess.
12. Suggestions must be realistic and concise.
13. Rewritten bullets must preserve the student's actual work.
14. Missing skills are learning recommendations, not claims that
    the student already knows them.

Your job is only to provide improvement guidance.
"""

    user_input = f"""
ANALYSIS CONTEXT:

{json.dumps(context, indent=2)}

RESUME TEXT:

{clean_text}
"""

    response = client.responses.create(
        model=MODEL_NAME,

        instructions=instructions,

        input=user_input,

        store=False,

        text={
            "format": {
                "type": "json_schema",
                "name": "resume_guidance",
                "strict": True,
                "schema": {
                    "type": "object",

                    "properties": {

                        "strengths": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            },
                        },

                        "weaknesses": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            },
                        },

                        "improvements": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            },
                        },

                        "summary_suggestion": {
                            "type": "string"
                        },

                        "project_bullet_suggestions": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            },
                        },

                        "learning_priorities": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            },
                        },

                        "ats_advice": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            },
                        },
                    },

                    "required": [
                        "strengths",
                        "weaknesses",
                        "improvements",
                        "summary_suggestion",
                        "project_bullet_suggestions",
                        "learning_priorities",
                        "ats_advice",
                    ],

                    "additionalProperties": False,
                },
            },

            "verbosity": "low",
        },
    )

    if not response.output_text:
        raise RuntimeError(
            "AI did not return resume guidance"
        )

    try:
        return json.loads(
            response.output_text
        )

    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "AI returned invalid structured output"
        ) from exc