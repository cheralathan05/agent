"""Approval management API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.database.models.approval import Approval
from backend.app.database.session import get_db

router = APIRouter(prefix="/api/v1/approvals", tags=["approvals"])


class ApproveRequest(BaseModel):
    permission_type: str = "once"  # once, session, always


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
    approval.status = "approved"
    approval.permission_type = request.permission_type
    db.commit()
    return {"id": approval_id, "status": "approved"}


@router.post("/{approval_id}/deny")
async def deny_request(approval_id: str, db: Session = Depends(get_db)):
    """Deny a pending approval request."""
    approval = db.query(Approval).filter(Approval.id == approval_id).first()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    approval.status = "denied"
    db.commit()
    return {"id": approval_id, "status": "denied"}
