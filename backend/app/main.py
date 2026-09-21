from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.core.config import settings
from app.db.session import engine
from app.db.base import Base

from app.api.routes import (
    auth,
    users,
    students,
    recruiters,
    opportunities,
    resumes,
    career,
    chat,
    recruiter_chat,
    notifications,
    colleges,
    collaborations,
    challenges,
    admin,
    college_chat,
)


# ============================================================
# DATABASE
# ============================================================

Base.metadata.create_all(bind=engine)


# ============================================================
# APP
# ============================================================

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "AI-powered Academia-Industry Collaboration, "
        "Skill Intelligence, Internship and Placement Platform"
    ),
)


# ============================================================
# PATHS
#
# main.py:
# backend/app/main.py
#
# templates:
# backend/templates/
#
# static:
# backend/static/
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"


templates = Jinja2Templates(
    directory=str(TEMPLATES_DIR)
)


# ============================================================
# STATIC FILES
# ============================================================

app.mount(
    "/assets",
    StaticFiles(
        directory=str(STATIC_DIR / "assets")
    ),
    name="assets",
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://skillbridge-ai-sand.vercel.app",
        "https://skillnexus-ai.onrender.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# API ROUTERS
# ============================================================

for r in [
    auth,
    users,
    students,
    recruiters,
    opportunities,
    resumes,
    career,
    chat,
    recruiter_chat,
    notifications,
    colleges,
    collaborations,
    challenges,
    admin,
    college_chat,
]:
    app.include_router(
        r.router,
        prefix="/api/v1",
    )


# ============================================================
# ADMIN FRONTEND ROUTES
# ============================================================

@app.get(
    "/",
    include_in_schema=False,
)
def root():
    return RedirectResponse(
        url="/admin/login"
    )


@app.get(
    "/admin",
    include_in_schema=False,
)
def admin_root():
    return RedirectResponse(
        url="/admin/login"
    )


@app.get(
    "/admin/login",
    include_in_schema=False,
)
def admin_login(
    request: Request,
):
    return templates.TemplateResponse(
        request=request,
        name="admin/login.html",
        context={},
    )


@app.get(
    "/admin/dashboard",
    include_in_schema=False,
)
def admin_dashboard(
    request: Request,
):
    return templates.TemplateResponse(
        request=request,
        name="admin/dashboard.html",
        context={},
    )


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "SkillBridge AI Backend",
    }
