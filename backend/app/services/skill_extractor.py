import re

KNOWN_SKILLS = {

    "python": ["python"],
    "django": ["django"],
    "fastapi": ["fastapi", "fast api"],
    "flask": ["flask"],

    "javascript": ["javascript", "js"],
    "typescript": ["typescript"],
    "react": ["react", "react.js"],
    "next.js": ["next.js", "nextjs"],

    "html": ["html"],
    "css": ["css"],
    "postgresql": ["postgresql", "postgres"],
    "mysql": ["mysql"],
    "sql": ["sql"],

    "mongodb": ["mongodb"],
    "redis": ["redis"],
    "git": ["git"],
    "github": ["github"],
    "docker": ["docker"],

    "kubernetes": ["kubernetes", "k8s"],
    "aws": ["aws", "amazon web services"],
    "azure": ["azure"],
    "rest api": ["rest api", "restful api"],

    "sqlalchemy": ["sqlalchemy"],
    "jwt": ["jwt", "json web token"],
    "machine learning": ["machine learning"],

    "artificial intelligence": ["artificial intelligence", "ai"],
    "pandas": ["pandas"],
    "numpy": ["numpy"],

    "tensorflow": ["tensorflow"],
    "pytorch": ["pytorch"],
    "java": ["java"],
    "c++": ["c++"],
    "c": ["c language", " c "]

}


def extract_skills(text: str) -> list[dict]:

    t = text.lower()
    out = []

    for name, aliases in KNOWN_SKILLS.items():

        if any(
            re.search(
                rf"(?<!\w){re.escape(a)}(?!\w)",
                t
            )
            for a in aliases
        ):

            out.append({
                "name": name,
                "confidence": 1.0
            })

    return out