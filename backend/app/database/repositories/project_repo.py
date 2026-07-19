"""Project repository for database operations."""

from sqlalchemy.orm import Session

from backend.app.database.models.project import Project


class ProjectRepository:
    """Repository for Project CRUD operations."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_path(self, path: str) -> Project | None:
        return self.db.query(Project).filter(Project.path == path).first()

    def get_by_id(self, project_id: str) -> Project | None:
        return self.db.query(Project).filter(Project.id == project_id).first()

    def list_all(self) -> list[Project]:
        return self.db.query(Project).order_by(Project.updated_at.desc()).all()

    def create(self, name: str, path: str, **kwargs) -> Project:
        project = Project(name=name, path=path, **kwargs)
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        return project

    def update(self, project_id: str, **kwargs) -> Project | None:
        project = self.get_by_id(project_id)
        if project:
            for key, value in kwargs.items():
                if hasattr(project, key) and value is not None:
                    setattr(project, key, value)
            self.db.commit()
            self.db.refresh(project)
        return project
