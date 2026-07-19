"""Spec-compliant /api/v1/runs endpoints."""

from fastapi import APIRouter, HTTPException

from backend.app.agent.orchestrator import orchestrator

router = APIRouter(prefix="/api/v1/runs", tags=["runs"])


@router.get("/{run_id}")
async def get_run(run_id: str):
    """Get the status and details of a run."""
    run_info = await orchestrator.get_run_status(run_id)
    if not run_info:
        raise HTTPException(status_code=404, detail="Run not found")
    return run_info


@router.post("/{run_id}/cancel")
async def cancel_run(run_id: str):
    """Cancel an active run."""
    result = await orchestrator.cancel_run(run_id)
    if not result:
        raise HTTPException(status_code=404, detail="Run not found or already completed")
    return {"run_id": run_id, "status": "cancelled"}


@router.get("/{run_id}/events")
async def get_run_events(run_id: str):
    """Get events for a run."""
    run_info = await orchestrator.get_run_status(run_id)
    if not run_info:
        raise HTTPException(status_code=404, detail="Run not found")
    return {"run_id": run_id, "events": []}


@router.get("/{run_id}/diff")
async def get_run_diff(run_id: str):
    """Get the diff of changes made by a run."""
    return {"run_id": run_id, "diff": ""}
