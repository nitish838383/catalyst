from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db

from app.models.user import User, UserRole
from app.models.college import College

from app.models.college_chat import (
    CollegeChatSession,
    CollegeChatMessage,
)

from app.schemas.college_chat import (
    CollegeChatSessionCreate,
    CollegeChatMessageCreate,
)

from app.services.college_context import (
    build_college_context,
)

from app.services.ai_college import (
    generate_college_response,
)


router = APIRouter(
    prefix="/college-chat",
    tags=["College AI Chat"]
)


# ============================================================
# Helper - Get Logged-in College
# ============================================================

def get_current_college(
    db: Session,
    user_id: int
):
    college = (
        db.query(College)
        .filter(
            College.user_id == user_id
        )
        .first()
    )

    if not college:
        raise HTTPException(
            status_code=404,
            detail="College profile not found"
        )

    return college


# ============================================================
# CREATE CHAT SESSION
# ============================================================

@router.post("/sessions")
def create_session(
    data: CollegeChatSessionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.college)
    ),
):
    college = get_current_college(
        db,
        user.id
    )

    row = CollegeChatSession(
        college_id=college.id,
        title=(
            data.title
            or "College AI Assistant"
        )
    )

    db.add(row)
    db.commit()
    db.refresh(row)

    return {
        "success": True,
        "message": "College chat session created",
        "data": {
            "id": row.id,
            "session_id": row.id,
            "title": row.title,
            "created_at": row.created_at,
        }
    }


# ============================================================
# GET CHAT SESSIONS
# ============================================================

@router.get("/sessions")
def get_sessions(
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.college)
    ),
):
    college = get_current_college(
        db,
        user.id
    )

    rows = (
        db.query(CollegeChatSession)
        .filter(
            CollegeChatSession.college_id
            == college.id
        )
        .order_by(
            CollegeChatSession.created_at.desc()
        )
        .all()
    )

    return {
        "success": True,
        "data": [
            {
                "id": row.id,
                "session_id": row.id,
                "title": row.title,
                "created_at": row.created_at,
            }
            for row in rows
        ]
    }


# ============================================================
# GET SESSION MESSAGES
# ============================================================

@router.get(
    "/sessions/{session_id}/messages"
)
def get_messages(
    session_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.college)
    ),
):
    college = get_current_college(
        db,
        user.id
    )

    session = (
        db.query(CollegeChatSession)
        .filter(
            CollegeChatSession.id
            == session_id,

            CollegeChatSession.college_id
            == college.id
        )
        .first()
    )

    if not session:
        raise HTTPException(
            status_code=404,
            detail="Chat session not found"
        )

    messages = (
        db.query(CollegeChatMessage)
        .filter(
            CollegeChatMessage.session_id
            == session.id
        )
        .order_by(
            CollegeChatMessage.created_at.asc()
        )
        .all()
    )

    return {
        "success": True,
        "data": [
            {
                "id": message.id,
                "role": message.role,
                "content": message.content,
                "created_at": message.created_at,
            }
            for message in messages
        ]
    }


# ============================================================
# SEND MESSAGE
# ============================================================

@router.post(
    "/sessions/{session_id}/messages"
)
def send_message(
    session_id: int,
    data: CollegeChatMessageCreate,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.college)
    ),
):
    college = get_current_college(
        db,
        user.id
    )

    # --------------------------------------------------------
    # Check session belongs to logged-in college
    # --------------------------------------------------------

    session = (
        db.query(CollegeChatSession)
        .filter(
            CollegeChatSession.id
            == session_id,

            CollegeChatSession.college_id
            == college.id
        )
        .first()
    )

    if not session:
        raise HTTPException(
            status_code=404,
            detail="Chat session not found"
        )


    # --------------------------------------------------------
    # Previous messages
    # --------------------------------------------------------

    previous_messages = (
        db.query(CollegeChatMessage)
        .filter(
            CollegeChatMessage.session_id
            == session.id
        )
        .order_by(
            CollegeChatMessage.created_at.asc()
        )
        .all()
    )

    history = [
        {
            "role": message.role,
            "content": message.content,
        }
        for message in previous_messages[-10:]
    ]


    # --------------------------------------------------------
    # Save user message
    # --------------------------------------------------------

    user_message = CollegeChatMessage(
        session_id=session.id,
        role="user",
        content=data.message.strip()
    )

    db.add(user_message)
    db.commit()


    # --------------------------------------------------------
    # Build REAL college context
    # --------------------------------------------------------

    college_context = build_college_context(
        db,
        college
    )


    # --------------------------------------------------------
    # Generate AI response
    # --------------------------------------------------------

    answer = generate_college_response(
        college_context=college_context,
        user_message=data.message,
        conversation_history=history,
    )


    # --------------------------------------------------------
    # Save assistant response
    # --------------------------------------------------------

    assistant_message = CollegeChatMessage(
        session_id=session.id,
        role="assistant",
        content=answer
    )

    db.add(assistant_message)
    db.commit()
    db.refresh(assistant_message)


    return {
        "success": True,
        "message": "College AI response generated",
        "data": {
            "answer": answer,
            "message_id": assistant_message.id,
        }
    }