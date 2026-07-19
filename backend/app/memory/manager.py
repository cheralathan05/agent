"""Memory manager for persistent knowledge storage."""

from __future__ import annotations

from typing import Any

from backend.app.database.models.failure_record import FailureRecord
from backend.app.database.models.memory import Memory
from backend.app.database.models.project_decision import ProjectDecision
from backend.app.database.session import SessionLocal


class MemoryManager:
    """Manages different types of memory for the agent."""

    async def store(
        self,
        memory_type: str,
        key: str,
        content: str,
        project_id: str | None = None,
        summary: str | None = None,
        importance: int = 0,
    ) -> str:
        """Store a memory entry."""
        db = SessionLocal()
        try:
            memory = Memory(
                project_id=project_id,
                memory_type=memory_type,
                key=key,
                content=content,
                summary=summary or content[:200],
                importance=importance,
            )
            db.add(memory)
            db.commit()
            return memory.id
        finally:
            db.close()

    async def retrieve(
        self,
        key: str,
        project_id: str | None = None,
        memory_type: str | None = None,
    ) -> str | None:
        """Retrieve a memory entry by key."""
        db = SessionLocal()
        try:
            query = db.query(Memory).filter(Memory.key == key)
            if project_id:
                query = query.filter(Memory.project_id == project_id)
            if memory_type:
                query = query.filter(Memory.memory_type == memory_type)
            memory = query.order_by(Memory.updated_at.desc()).first()
            return memory.content if memory else None
        finally:
            db.close()

    async def search(
        self,
        query: str,
        project_id: str | None = None,
        memory_type: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search memory entries."""
        db = SessionLocal()
        try:
            q = db.query(Memory)
            if project_id:
                q = q.filter(Memory.project_id == project_id)
            if memory_type:
                q = q.filter(Memory.memory_type == memory_type)

            # Simple keyword search on key and content
            keyword = f"%{query}%"
            q = q.filter(
                (Memory.key.like(keyword)) | (Memory.content.like(keyword))
            )
            memories = q.order_by(Memory.importance.desc()).limit(limit).all()

            return [
                {
                    "id": m.id,
                    "memory_type": m.memory_type,
                    "key": m.key,
                    "summary": m.summary,
                    "importance": m.importance,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
                for m in memories
            ]
        finally:
            db.close()

    async def forget(self, memory_id: str) -> bool:
        """Delete a memory entry."""
        db = SessionLocal()
        try:
            memory = db.query(Memory).filter(Memory.id == memory_id).first()
            if memory:
                db.delete(memory)
                db.commit()
                return True
            return False
        finally:
            db.close()

    async def store_failure(
        self,
        project_id: str,
        error_message: str,
        cause: str,
        fix: str,
        verification: str | None = None,
    ) -> str:
        """Store a failure record for learning."""
        db = SessionLocal()
        try:
            record = FailureRecord(
                project_id=project_id,
                error_message=error_message,
                cause=cause,
                fix=fix,
                verification=verification,
            )
            db.add(record)
            db.commit()
            return record.id
        finally:
            db.close()

    async def find_similar_failure(
        self,
        error_message: str,
        project_id: str,
    ) -> dict[str, Any] | None:
        """Find a similar failure in memory."""
        db = SessionLocal()
        try:
            keyword = f"%{error_message[:100]}%"
            record = (
                db.query(FailureRecord)
                .filter(
                    FailureRecord.project_id == project_id,
                    FailureRecord.error_message.like(keyword),
                )
                .first()
            )
            if record:
                return {
                    "cause": record.cause,
                    "fix": record.fix,
                    "verification": record.verification,
                }
            return None
        finally:
            db.close()

    async def store_decision(
        self,
        project_id: str,
        title: str,
        description: str,
        rationale: str | None = None,
    ) -> str:
        """Store an architectural decision."""
        db = SessionLocal()
        try:
            decision = ProjectDecision(
                project_id=project_id,
                title=title,
                description=description,
                rationale=rationale,
            )
            db.add(decision)
            db.commit()
            return decision.id
        finally:
            db.close()


# Global memory manager
memory_manager = MemoryManager()
