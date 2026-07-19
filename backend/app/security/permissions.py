"""Permission engine for tool/command authorization."""

from __future__ import annotations

from typing import Any

from backend.app.database.models.approval import Approval
from backend.app.database.models.permission import Permission
from backend.app.database.session import SessionLocal


class PermissionEngine:
    """Manages tool execution permissions with allow-once/session/always/deny."""

    def __init__(self):
        self._session_permissions: dict[str, str] = {}  # tool_name -> permission

    async def check_permission(
        self,
        tool_name: str,
        action: str,
        reason: str,
        risk: str = "low",
        run_id: str | None = None,
    ) -> dict[str, Any]:
        """Check if a tool action is permitted.
        
        Returns:
            Dict with 'permitted' (bool) and optionally 'approval_id' for pending approvals.
        """
        # Check session-level permissions first
        session_perm = self._session_permissions.get(tool_name)
        if session_perm == "always":
            return {"permitted": True}
        if session_perm == "denied":
            return {"permitted": False, "reason": "Permission denied for this session"}

        # Check persisted permissions
        db = SessionLocal()
        try:
            saved = (
                db.query(Permission)
                .filter(Permission.tool_name == tool_name)
                .first()
            )
            if saved:
                if saved.permission == "always":
                    self._session_permissions[tool_name] = "always"
                    return {"permitted": True}
                elif saved.permission == "denied":
                    return {"permitted": False}
        finally:
            db.close()

        # No cached permission - requires approval for non-safe actions
        if risk in ("medium", "high"):
            approval_id = None
            if run_id:
                db = SessionLocal()
                try:
                    approval = Approval(
                        run_id=run_id,
                        tool_name=tool_name,
                        action=action,
                        reason=reason,
                        risk=risk,
                        status="pending",
                    )
                    db.add(approval)
                    db.commit()
                    approval_id = approval.id
                finally:
                    db.close()

            return {
                "permitted": False,
                "requires_approval": True,
                "approval_id": approval_id,
                "message": f"Approval needed: {reason}",
            }

        return {"permitted": True}

    async def grant_permission(
        self,
        tool_name: str,
        permission: str = "once",
    ):
        """Grant permission for a tool."""
        if permission == "session":
            self._session_permissions[tool_name] = "always"
        elif permission == "always":
            db = SessionLocal()
            try:
                existing = (
                    db.query(Permission)
                    .filter(Permission.tool_name == tool_name)
                    .first()
                )
                if existing:
                    existing.permission = "always"
                else:
                    saved = Permission(
                        tool_name=tool_name, permission="always"
                    )
                    db.add(saved)
                db.commit()
            finally:
                db.close()
            self._session_permissions[tool_name] = "always"

    async def deny_permission(self, tool_name: str):
        """Deny permission for a tool."""
        self._session_permissions[tool_name] = "denied"

    def clear_session(self):
        """Clear all session-level permissions."""
        self._session_permissions.clear()


# Global permission engine
permission_engine = PermissionEngine()
