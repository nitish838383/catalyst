from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
    notifications,
    colleges,
    collaborations,
    challenges,
    admin,
)

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered Academia-Industry Collaboration, Skill Intelligence, Internship and Placement Platform",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://skillbridge-ai-sand.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in [
    auth,
    users,
    students,
    recruiters,
    opportunities,
    resumes,
    career,
    chat,
    notifications,
    colleges,
    collaborations,
    challenges,
    admin,
]:
    app.include_router(
        r.router,
        prefix="/api/v1",
    )


@app.get("/")
def root():
    return {
        "success": True,
        "message": "SkillBridge AI API is running",
        "version": settings.APP_VERSION,
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "SkillBridge AI Backend",
    }