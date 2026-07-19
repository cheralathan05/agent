"""Agent run API endpoints."""

from fastapi import APIRouter
from pydantic import BaseModel

from backend.app.agent.loop import AgentLoop

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])


class AgentRunRequest(BaseModel):
    goal: str
    session_id: str
    model: str | None = None
    workspace: str | None = None


@router.post("/run")
async def start_agent_run(request: AgentRunRequest):
    """Start an agent run for a given goal."""
    loop = AgentLoop()
    run_id = await loop.run(
        session_id=request.session_id,
        goal=request.goal,
        model=request.model,
        workspace=request.workspace,
    )
    return {"run_id": run_id, "status": "started"}
