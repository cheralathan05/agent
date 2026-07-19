"""Tool listing API endpoint."""

from fastapi import APIRouter

from backend.app.tools.registry import registry

router = APIRouter(prefix="/api/v1/tools", tags=["tools"])


@router.get("")
async def list_tools():
    """List all registered tools."""
    tools = registry.list_tools()
    return {"tools": tools, "count": len(tools)}


@router.get("/permissions")
async def list_permissions():
    """List all permission requirements for tools."""
    tools = registry.list_tools()
    permissions = [
        {
            "name": t["name"],
            "risk_level": t["risk_level"],
            "permission_requirement": t["permission_requirement"],
        }
        for t in tools
    ]
    return {"permissions": permissions}
