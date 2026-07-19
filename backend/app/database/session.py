"""Database engine and session management."""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from backend.app.config import settings


class Base(DeclarativeBase):
    pass


# Sync engine for Alembic and direct usage
engine = create_engine(
    settings.database_sync_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_sync_url else {},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependency that provides a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables."""
    import backend.app.database.models  # noqa: F401 - ensure models are imported
    Base.metadata.create_all(bind=engine)
