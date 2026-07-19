"""Project management API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.database.models.project import Project
from backend.app.database.session import get_db

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


class ProjectCreate(BaseModel):
    name: str
    path: str
    description: str | None = None


@router.post("")
async def create_project(request: ProjectCreate, db: Session = Depends(get_db)):
    """Register a project."""
    existing = db.query(Project).filter(Project.path == request.path).first()
    if existing:
        return {"id": existing.id, "name": existing.name, "exists": True}
    
    project = Project(name=request.name, path=request.path, description=request.description)
    db.add(project)
    db.commit()
    db.refresh(project)
    return {"id": project.id, "name": project.name, "exists": False}


@router.get("")
async def list_projects(db: Session = Depends(get_db)):
    """List all projects."""
    projects = db.query(Project).order_by(Project.updated_at.desc()).all()
    return {
        "projects": [
            {
                "id": p.id,
                "name": p.name,
                "path": p.path,
                "language": p.language,
                "framework": p.framework,
                "git_branch": p.git_branch,
            }
            for p in projects
        ]
    }


@router.get("/{project_id}")
async def get_project(project_id: str, db: Session = Depends(get_db)):
    """Get a project by ID."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return {
        "id": project.id,
        "name": project.name,
        "path": project.path,
        "language": project.language,
        "framework": project.framework,
        "git_branch": project.git_branch,
        "metadata": project.metadata,
    }
