import re


KNOWN_SKILLS = {
    "Python": ["python"],
    "Django": ["django"],
    "FastAPI": ["fastapi", "fast api"],
    "Flask": ["flask"],

    "JavaScript": [
        "javascript",
        "js",
    ],

    "TypeScript": [
        "typescript",
    ],

    "React": [
        "react",
        "react.js",
        "reactjs",
    ],

    "Next.js": [
        "next.js",
        "nextjs",
    ],

    "HTML": [
        "html",
        "html5",
    ],

    "CSS": [
        "css",
        "css3",
    ],

    "PostgreSQL": [
        "postgresql",
        "postgres",
    ],

    "MySQL": [
        "mysql",
    ],

    "SQL": [
        "sql",
    ],

    "MongoDB": [
        "mongodb",
        "mongo db",
    ],

    "Redis": [
        "redis",
    ],

    "Git": [
        "git",
    ],

    "GitHub": [
        "github",
    ],

    "Docker": [
        "docker",
    ],

    "Kubernetes": [
        "kubernetes",
        "k8s",
    ],

    "AWS": [
        "aws",
        "amazon web services",
    ],

    "Azure": [
        "azure",
        "microsoft azure",
    ],

    "REST API": [
        "rest api",
        "restful api",
        "restful services",
    ],

    "SQLAlchemy": [
        "sqlalchemy",
    ],

    "JWT": [
        "jwt",
        "json web token",
    ],

    "Machine Learning": [
        "machine learning",
    ],

    "Artificial Intelligence": [
        "artificial intelligence",
    ],

    "Pandas": [
        "pandas",
    ],

    "NumPy": [
        "numpy",
    ],

    "TensorFlow": [
        "tensorflow",
    ],

    "PyTorch": [
        "pytorch",
    ],

    "Java": [
        "java",
    ],

    "C++": [
        "c++",
        "cpp",
    ],

    "C": [
        "c language",
        "c programming",
    ],
}


def extract_skills(text: str) -> list[dict]:
    normalized_text = text.lower()

    detected_skills = []

    for name, aliases in KNOWN_SKILLS.items():

        for alias in aliases:

            pattern = (
                rf"(?<!\w)"
                rf"{re.escape(alias.lower())}"
                rf"(?!\w)"
            )

            if re.search(
                pattern,
                normalized_text,
                flags=re.IGNORECASE,
            ):
                detected_skills.append({
                    "name": name,
                    "confidence": 1.0,
                    "source": "resume",
                })

                break

    return detected_skills