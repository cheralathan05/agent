"""Memory management API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.database.models.memory import Memory
from backend.app.database.session import get_db

router = APIRouter(prefix="/api/v1/memory", tags=["memory"])


class MemoryCreate(BaseModel):
    memory_type: str = "conversation"
    key: str
    content: str
    project_id: str | None = None


@router.get("")
async def list_memory(
    project_id: str | None = None,
    memory_type: str | None = None,
    db: Session = Depends(get_db),
):
    """List memories with optional filtering."""
    query = db.query(Memory)
    if project_id:
        query = query.filter(Memory.project_id == project_id)
    if memory_type:
        query = query.filter(Memory.memory_type == memory_type)

    memories = query.order_by(Memory.updated_at.desc()).limit(50).all()
    return {
        "memories": [
            {
                "id": m.id,
                "memory_type": m.memory_type,
                "key": m.key,
                "summary": m.summary,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in memories
        ]
    }


@router.delete("/{memory_id}")
async def delete_memory(memory_id: str, db: Session = Depends(get_db)):
    """Delete a memory entry."""
    memory = db.query(Memory).filter(Memory.id == memory_id).first()
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    db.delete(memory)
    db.commit()
    return {"deleted": memory_id}
