"""Spec-compliant /api/v1/runs endpoints with diff computation."""

from __future__ import annotations

import asyncio
import difflib
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.agent.orchestrator import orchestrator
from backend.app.config import settings
from backend.app.database.models.file_change import FileChange
from backend.app.database.session import get_db

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


def _compute_inline_diff(old_content: str | None, new_content: str | None) -> str | None:
    """Compute a unified diff string from old/new content using difflib."""
    if old_content is None and new_content is None:
        return None
    old_lines = (old_content or "").splitlines(keepends=True)
    new_lines = (new_content or "").splitlines(keepends=True)
    diff_lines = list(
        difflib.unified_diff(old_lines, new_lines, fromfile="original", tofile="modified", n=3)
    )
    return "".join(diff_lines) if diff_lines else None


def _parse_git_diff(git_diff: str) -> list[dict]:
    """Parse a git unified diff string into file-level change dicts."""
    diffs: list[dict] = []
    current_file = None
    current_diff_lines: list[str] = []

    def flush_file():
        nonlocal current_file, current_diff_lines
        if current_file and current_diff_lines:
            body = "\n".join(current_diff_lines)
            added = sum(1 for l in current_diff_lines if l.startswith("+") and not l.startswith("+++"))
            removed = sum(1 for l in current_diff_lines if l.startswith("-") and not l.startswith("---"))
            diffs.append({
                "id": None,
                "file_path": current_file,
                "change_type": "modify",
                "old_content": None,
                "new_content": None,
                "diff": body,
                "lines_added": added,
                "lines_removed": removed,
                "status": "pending",
            })
            current_diff_lines = []

    for line in git_diff.split("\n"):
        if line.startswith("diff --git"):
            flush_file()
            parts = line.split(" b/")
            current_file = parts[-1] if len(parts) > 1 else parts[0].split(" a/")[-1]
        elif line.startswith("--- ") or line.startswith("+++ "):
            continue
        elif line.startswith("@@") and " @@" in line:
            current_diff_lines.append(line)
        elif current_file:
            current_diff_lines.append(line)

    flush_file()
    return diffs


@router.get("/{run_id}/diff")
async def get_run_diff(run_id: str, db: Session = Depends(get_db)):
    """Get the diff of changes made by a run.

    Builds diffs from:
    1. FileChange records stored during the run (computes inline diff when needed)
    2. Git working-tree / staged diffs as a fallback
    """
    changes = db.query(FileChange).filter(
        FileChange.run_id == run_id,
    ).all()

    diffs: list[dict] = []

    for c in changes:
        # Use stored diff, or compute one from old/new content
        diff_text = c.diff
        if not diff_text and (c.old_content is not None or c.new_content is not None):
            diff_text = _compute_inline_diff(c.old_content, c.new_content)

        diffs.append({
            "id": c.id,
            "file_path": c.file_path,
            "change_type": c.change_type,
            "old_content": c.old_content,
            "new_content": c.new_content,
            "diff": diff_text,
            "lines_added": c.lines_added,
            "lines_removed": c.lines_removed,
            "status": c.status,
        })

    # Fallback: try git diff (working tree + staged) when no stored changes
    if not changes:
        ws = Path(settings.workspace_path).resolve()
        for git_cmd in [["git", "diff", "HEAD"], ["git", "diff"], ["git", "diff", "--cached"]]:
            try:
                proc = await asyncio.create_subprocess_exec(
                    *git_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=str(ws),
                )
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
                git_diff = stdout.decode("utf-8", errors="replace")
                if git_diff.strip():
                    diffs = _parse_git_diff(git_diff)
                    break
            except (asyncio.TimeoutError, FileNotFoundError, PermissionError):
                continue

    return {
        "run_id": run_id,
        "files": diffs,
        "total_changes": len(diffs),
        "total_added": sum(d["lines_added"] for d in diffs or []),
        "total_removed": sum(d["lines_removed"] for d in diffs or []),
    }


class FileActionRequest(BaseModel):
    status: str  # accepted or rejected


@router.post("/{run_id}/diff/{change_id}")
async def update_file_status(
    run_id: str, change_id: str, request: FileActionRequest, db: Session = Depends(get_db),
):
    """Accept or reject a specific file change."""
    change = db.query(FileChange).filter(
        FileChange.id == change_id,
        FileChange.run_id == run_id,
    ).first()
    if not change:
        raise HTTPException(status_code=404, detail="Change not found")

    if request.status not in ("accepted", "rejected"):
        raise HTTPException(status_code=422, detail="Status must be 'accepted' or 'rejected'")

    change.status = request.status
    db.commit()
    return {"id": change_id, "status": request.status}
