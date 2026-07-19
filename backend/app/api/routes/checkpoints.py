"""Checkpoint API endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.checkpoints.manager import checkpoint_manager

router = APIRouter(prefix="/api/v1/checkpoints", tags=["checkpoints"])


class CheckpointCreate(BaseModel):
    description: str
    project_id: str | None = None
    run_id: str | None = None


@router.post("")
async def create_checkpoint(request: CheckpointCreate):
    """Create a new checkpoint."""
    result = await checkpoint_manager.create_checkpoint(
        description=request.description,
        project_id=request.project_id,
        run_id=request.run_id,
    )
    return result


@router.get("")
async def list_checkpoints(
    run_id: str | None = None,
    project_id: str | None = None,
):
    """List checkpoints with optional filtering."""
    result = await checkpoint_manager.list_checkpoints(
        run_id=run_id, project_id=project_id
    )
    return {"checkpoints": result, "count": len(result)}


@router.post("/{checkpoint_id}/restore")
async def restore_checkpoint(checkpoint_id: str):
    """Restore workspace to a checkpoint."""
    result = await checkpoint_manager.restore_checkpoint(checkpoint_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Restore failed"))
    return result


@router.delete("/{checkpoint_id}")
async def delete_checkpoint(checkpoint_id: str):
    """Delete a checkpoint."""
    result = await checkpoint_manager.delete_checkpoint(checkpoint_id)
    if not result:
        raise HTTPException(status_code=404, detail="Checkpoint not found")
    return {"deleted": checkpoint_id}
