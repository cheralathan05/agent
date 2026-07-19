"""Execution history API endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.database.models.agent_run import AgentRun
from backend.app.database.session import get_db

router = APIRouter(prefix="/api/v1/executions", tags=["executions"])


@router.get("")
async def list_executions(
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """List recent agent executions."""
    runs = (
        db.query(AgentRun)
        .order_by(AgentRun.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        "executions": [
            {
                "id": r.id,
                "goal": r.goal[:100],
                "status": r.status,
                "model": r.model,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "current_step": r.current_step,
                "total_steps": r.total_steps,
                "duration_ms": r.duration_ms,
            }
            for r in runs
        ],
        "total": len(runs),
    }
