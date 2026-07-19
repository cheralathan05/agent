"""Session management API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.database.models.session import Session as SessionModel
from backend.app.database.session import get_db

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


class SessionCreate(BaseModel):
    title: str = "New Session"
    project_id: str | None = None


class SessionUpdate(BaseModel):
    title: str | None = None
    status: str | None = None


@router.post("")
async def create_session(
    request: SessionCreate,
    db: Session = Depends(get_db),
):
    """Create a new session."""
    session = SessionModel(title=request.title, project_id=request.project_id)
    db.add(session)
    db.commit()
    db.refresh(session)
    return {"id": session.id, "title": session.title, "status": session.status}


@router.get("")
async def list_sessions(db: Session = Depends(get_db)):
    """List all active sessions."""
    sessions = db.query(SessionModel).order_by(SessionModel.updated_at.desc()).all()
    return {
        "sessions": [
            {"id": s.id, "title": s.title, "status": s.status, "created_at": s.created_at.isoformat() if s.created_at else None}
            for s in sessions
        ]
    }


@router.get("/{session_id}")
async def get_session(session_id: str, db: Session = Depends(get_db)):
    """Get a session by ID."""
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "id": session.id,
        "title": session.title,
        "status": session.status,
        "project_id": session.project_id,
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "updated_at": session.updated_at.isoformat() if session.updated_at else None,
    }


@router.post("/{session_id}")
async def update_session(session_id: str, request: SessionUpdate, db: Session = Depends(get_db)):
    """Update a session."""
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if request.title is not None:
        session.title = request.title
    if request.status is not None:
        session.status = request.status
    db.commit()
    return {"id": session.id, "title": session.title, "status": session.status}
