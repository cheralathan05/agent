"""Requirement Graph — tracks requirements through their full lifecycle.

Statuses: NOT_STARTED → IN_PROGRESS → IMPLEMENTED → VERIFIED → FAILED

Each requirement can be linked to:
  - Implementation (files changed)
  - Verification (test results)
  - Sessions / agent runs
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from backend.app.database.models.requirement import Requirement
from backend.app.database.session import SessionLocal


class RequirementGraph:
    """Tracks requirements through implementation and verification."""

    async def create_requirement(
        self,
        description: str,
        project_id: str,
        run_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a new requirement."""
        db = SessionLocal()
        try:
            req = Requirement(
                project_id=project_id,
                run_id=run_id,
                description=description,
                status="not_started",
            )
            db.add(req)
            db.commit()
            return {
                "id": req.id,
                "description": description,
                "status": "not_started",
                "created_at": req.created_at.isoformat() if req.created_at else None,
            }
        finally:
            db.close()

    async def update_status(
        self,
        requirement_id: str,
        status: str,
        verification_result: str | None = None,
    ) -> dict[str, Any] | None:
        """Update the status of a requirement."""
        valid_statuses = {"not_started", "in_progress", "implemented", "verified", "failed"}
        if status not in valid_statuses:
            return None

        db = SessionLocal()
        try:
            req = db.query(Requirement).filter(Requirement.id == requirement_id).first()
            if not req:
                return None

            req.status = status
            if verification_result:
                req.verification_result = verification_result
            db.commit()

            return {
                "id": req.id,
                "description": req.description,
                "status": req.status,
                "verification_result": req.verification_result,
                "updated_at": req.updated_at.isoformat() if req.updated_at else None,
            }
        finally:
            db.close()

    async def list_requirements(
        self,
        project_id: str,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        """List requirements for a project, optionally filtered by status."""
        db = SessionLocal()
        try:
            query = db.query(Requirement).filter(Requirement.project_id == project_id)
            if status:
                query = query.filter(Requirement.status == status)
            reqs = query.order_by(Requirement.created_at.desc()).all()

            return [
                {
                    "id": r.id,
                    "description": r.description[:100],
                    "status": r.status,
                    "has_verification": r.verification_result is not None,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in reqs
            ]
        finally:
            db.close()

    async def get_coverage(self, project_id: str) -> dict[str, Any]:
        """Get requirement coverage statistics for a project."""
        db = SessionLocal()
        try:
            all_reqs = db.query(Requirement).filter(Requirement.project_id == project_id).all()
            total = len(all_reqs)
            counts: dict[str, int] = {}
            for r in all_reqs:
                counts[r.status] = counts.get(r.status, 0) + 1

            return {
                "total": total,
                "by_status": counts,
                "completed": counts.get("verified", 0) + counts.get("implemented", 0),
                "failed": counts.get("failed", 0),
                "in_progress": counts.get("in_progress", 0),
                "not_started": counts.get("not_started", 0),
                "coverage_pct": round(
                    (counts.get("verified", 0) + counts.get("implemented", 0)) / max(total, 1) * 100, 1
                ),
            }
        finally:
            db.close()
