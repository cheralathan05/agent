"""Approval management API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.database.models.approval import Approval
from backend.app.database.session import get_db
from backend.app.security.permissions import permission_engine

router = APIRouter(prefix="/api/v1/approvals", tags=["approvals"])


class ApproveRequest(BaseModel):
    permission_type: str = "once"  # once, session, always


@router.get("")
async def list_approvals(
    status: str = Query("pending", description="Filter by status: pending, approved, denied"),
    run_id: str | None = None,
    db: Session = Depends(get_db),
):
    """List approvals with optional filtering."""
    query = db.query(Approval)
    if status:
        query = query.filter(Approval.status == status)
    if run_id:
        query = query.filter(Approval.run_id == run_id)

    approvals = query.order_by(Approval.created_at.desc()).limit(50).all()
    return {
        "approvals": [
            {
                "id": a.id,
                "run_id": a.run_id,
                "tool_name": a.tool_name,
                "action": a.action,
                "reason": a.reason,
                "risk": a.risk,
                "status": a.status,
                "permission_type": a.permission_type,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in approvals
        ],
        "count": len(approvals),
    }


@router.get("/{approval_id}")
async def get_approval(approval_id: str, db: Session = Depends(get_db)):
    """Get a single approval by ID."""
    approval = db.query(Approval).filter(Approval.id == approval_id).first()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    return {
        "id": approval.id,
        "run_id": approval.run_id,
        "tool_name": approval.tool_name,
        "action": approval.action,
        "reason": approval.reason,
        "risk": approval.risk,
        "status": approval.status,
        "permission_type": approval.permission_type,
        "created_at": approval.created_at.isoformat() if approval.created_at else None,
    }


@router.post("/{approval_id}/approve")
async def approve_request(
    approval_id: str,
    request: ApproveRequest,
    db: Session = Depends(get_db),
):
    """Approve a pending approval request."""
    approval = db.query(Approval).filter(Approval.id == approval_id).first()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    if approval.status != "pending":
        raise HTTPException(status_code=400, detail=f"Approval is already {approval.status}")

    approval.status = "approved"
    approval.permission_type = request.permission_type
    db.commit()

    # Grant permission to the permission engine
    await permission_engine.grant_permission(
        approval.tool_name, permission=request.permission_type
    )

    return {
        "id": approval_id,
        "status": "approved",
        "permission_type": request.permission_type,
    }


@router.post("/{approval_id}/deny")
async def deny_request(approval_id: str, db: Session = Depends(get_db)):
    """Deny a pending approval request."""
    approval = db.query(Approval).filter(Approval.id == approval_id).first()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    if approval.status != "pending":
        raise HTTPException(status_code=400, detail=f"Approval is already {approval.status}")

    approval.status = "denied"
    db.commit()

    # Deny permission in the engine
    await permission_engine.deny_permission(approval.tool_name)

    return {"id": approval_id, "status": "denied"}
