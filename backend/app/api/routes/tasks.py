"""Task management API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.database.models.task import Task
from backend.app.database.session import get_db

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


class TaskResponse(BaseModel):
    id: str
    run_id: str
    title: str
    status: str
    sequence: int


@router.get("/{run_id}")
async def list_tasks(run_id: str, db: Session = Depends(get_db)):
    """List all tasks for a run."""
    tasks = (
        db.query(Task)
        .filter(Task.run_id == run_id)
        .order_by(Task.sequence)
        .all()
    )
    return {
        "tasks": [
            {
                "id": t.id,
                "title": t.title,
                "status": t.status,
                "sequence": t.sequence,
                "assigned_agent": t.assigned_agent,
            }
            for t in tasks
        ]
    }
