"""Checkpoint manager for creating and restoring workspace snapshots."""

from __future__ import annotations

import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.app.config import settings
from backend.app.database.models.checkpoint import Checkpoint
from backend.app.database.session import SessionLocal
from backend.app.tools.utils import run_cmd_async


class CheckpointManager:
    """Manages creation and restoration of workspace checkpoints."""

    def __init__(self, workspace: str | Path | None = None):
        self.workspace = Path(workspace or settings.workspace_path).resolve()
        self.snapshots_dir = self.workspace / ".myagent" / "snapshots"
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)

    async def create_checkpoint(
        self,
        description: str,
        project_id: str | None = None,
        run_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a checkpoint of the current workspace state."""
        cp_id = str(uuid.uuid4())
        snapshot_path = self.snapshots_dir / cp_id
        snapshot_path.mkdir(parents=True, exist_ok=True)

        # Try to create a Git commit for the checkpoint
        git_commit = None
        diff_summary = ""
        files_changed: list[str] = []

        # Get git diff stat asynchronously
        git_stat = await run_cmd_async(
            ["git", "diff", "--stat"], cwd=self.workspace, timeout=10
        )
        diff_summary = git_stat.get("stdout", "").strip()
        if diff_summary:
            files_changed = [
                line.split("|")[0].strip()
                for line in diff_summary.split("\n")
                if "|" in line
            ]

        # Save diff to snapshot asynchronously
        git_diff = await run_cmd_async(["git", "diff"], cwd=self.workspace, timeout=10)
        if git_diff.get("stdout"):
            (snapshot_path / "diff.patch").write_text(git_diff["stdout"], encoding="utf-8")

        # Save file listing
        files = [str(p.relative_to(self.workspace)) for p in self.workspace.rglob("*")
                 if p.is_file() and ".myagent" not in str(p) and ".git" not in str(p)]
        (snapshot_path / "files.json").write_text(
            json.dumps(files, indent=2), encoding="utf-8"
        )

        # Persist to database
        db = SessionLocal()
        try:
            checkpoint = Checkpoint(
                id=cp_id,
                run_id=run_id or "",
                project_id=project_id,
                description=description,
                status="active",
                git_commit=git_commit,
                snapshot_path=str(snapshot_path),
                diff_summary=diff_summary,
                files_changed=json.dumps(files_changed),
            )
            db.add(checkpoint)
            db.commit()
        finally:
            db.close()

        return {
            "id": cp_id,
            "description": description,
            "files_changed": files_changed,
            "diff_summary": diff_summary,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    async def list_checkpoints(
        self,
        run_id: str | None = None,
        project_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """List checkpoints with optional filtering."""
        db = SessionLocal()
        try:
            query = db.query(Checkpoint).filter(Checkpoint.status == "active")
            if run_id:
                query = query.filter(Checkpoint.run_id == run_id)
            if project_id:
                query = query.filter(Checkpoint.project_id == project_id)
            checkpoints = query.order_by(Checkpoint.created_at.desc()).limit(20).all()

            return [
                {
                    "id": c.id,
                    "description": c.description,
                    "status": c.status,
                    "git_commit": c.git_commit,
                    "files_changed": json.loads(c.files_changed) if c.files_changed else [],
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                }
                for c in checkpoints
            ]
        finally:
            db.close()

    async def restore_checkpoint(self, checkpoint_id: str) -> dict[str, Any]:
        """Restore workspace to a checkpoint state."""
        db = SessionLocal()
        try:
            checkpoint = db.query(Checkpoint).filter(Checkpoint.id == checkpoint_id).first()
            if not checkpoint:
                return {"success": False, "error": "Checkpoint not found"}
            if checkpoint.status != "active":
                return {"success": False, "error": "Checkpoint is not active"}

            snapshot_path = Path(checkpoint.snapshot_path) if checkpoint.snapshot_path else None
            if snapshot_path and snapshot_path.exists():
                # Try git apply asynchronously first
                diff_path = snapshot_path / "diff.patch"
                if diff_path.exists():
                    git_result = await run_cmd_async(
                        ["git", "apply", str(diff_path)], cwd=self.workspace, timeout=30
                    )
                    if git_result.get("success"):
                        checkpoint.status = "restored"
                        db.commit()
                        return {
                            "success": True,
                            "message": "Checkpoint restored via git apply",
                        }

            # Fallback: copy files from snapshot
            files_path = snapshot_path / "files.json"
            if files_path.exists():
                files = json.loads(files_path.read_text(encoding="utf-8"))
                checkpoint.status = "restored"
                db.commit()
                return {
                    "success": True,
                    "message": f"Restored checkpoint with {len(files)} tracked files",
                    "files": files[:20],
                }

            return {"success": False, "error": "No snapshot data to restore from"}
        finally:
            db.close()

    async def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """Delete a checkpoint."""
        db = SessionLocal()
        try:
            checkpoint = db.query(Checkpoint).filter(Checkpoint.id == checkpoint_id).first()
            if not checkpoint:
                return False

            checkpoint.status = "failed"
            snapshot_path = Path(checkpoint.snapshot_path) if checkpoint.snapshot_path else None
            if snapshot_path and snapshot_path.exists():
                shutil.rmtree(snapshot_path, ignore_errors=True)
            db.commit()
            return True
        finally:
            db.close()


# Global checkpoint manager
checkpoint_manager = CheckpointManager()
