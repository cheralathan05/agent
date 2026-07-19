"""Agent orchestrator - manages the full agent lifecycle."""

import uuid
from datetime import datetime, timezone
from typing import Any

from backend.app.config import settings
from backend.app.database.models.agent_run import AgentRun
from backend.app.database.session import SessionLocal


class AgentOrchestrator:
    """Orchestrates agent runs from start to finish."""

    def __init__(self):
        self.active_runs: dict[str, dict[str, Any]] = {}

    async def create_run(
        self,
        session_id: str,
        goal: str,
        model: str | None = None,
        workspace: str | None = None,
    ) -> str:
        """Create a new agent run."""
        run_id = str(uuid.uuid4())

        db = SessionLocal()
        try:
            db_run = AgentRun(
                id=run_id,
                session_id=session_id,
                goal=goal,
                status="pending",
                model=model or settings.ollama_model,
                provider="ollama",
                workspace=workspace or str(settings.workspace_path),
                current_step=0,
                total_steps=0,
            )
            db.add(db_run)
            db.commit()
        finally:
            db.close()

        self.active_runs[run_id] = {
            "id": run_id,
            "session_id": session_id,
            "goal": goal,
            "status": "pending",
            "started_at": datetime.now(timezone.utc).isoformat(),
        }

        return run_id

    async def cancel_run(self, run_id: str) -> bool:
        """Cancel an active run."""
        if run_id in self.active_runs:
            self.active_runs[run_id]["status"] = "cancelled"

            db = SessionLocal()
            try:
                db_run = db.query(AgentRun).filter(AgentRun.id == run_id).first()
                if db_run:
                    db_run.status = "cancelled"
                    db.commit()
            finally:
                db.close()

            return True
        return False

    async def get_run_status(self, run_id: str) -> dict[str, Any] | None:
        """Get the current status of a run."""
        return self.active_runs.get(run_id)

    async def update_run(self, run_id: str, updates: dict[str, Any]):
        """Update a run's state."""
        if run_id in self.active_runs:
            self.active_runs[run_id].update(updates)

        db = SessionLocal()
        try:
            db_run = db.query(AgentRun).filter(AgentRun.id == run_id).first()
            if db_run:
                for key, value in updates.items():
                    if hasattr(db_run, key):
                        setattr(db_run, key, value)
                db.commit()
        finally:
            db.close()


# Global orchestrator instance
orchestrator = AgentOrchestrator()
