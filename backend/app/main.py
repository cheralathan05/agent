"""FastAPI application entry point."""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.routes import (
    health,
    chat,
    sessions,
    projects,
    models,
    agents,
    tasks,
    tools,
    memory as memory_routes,
    approvals,
    executions,
    settings as settings_routes,
    runs,
    checkpoints,
)
from backend.app.api.websocket import router as websocket_router
from backend.app.config import settings
from backend.app.database.session import init_db
from backend.app.llm.router import close_providers
from backend.app.tools.registry import init_tools

app = FastAPI(
    title="MyAgent API",
    description="Local Autonomous AI Coding Agent Platform",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(chat.router)
app.include_router(sessions.router)
app.include_router(projects.router)
app.include_router(models.router)
app.include_router(agents.router)
app.include_router(tasks.router)
app.include_router(tools.router)
app.include_router(memory_routes.router)
app.include_router(approvals.router)
app.include_router(executions.router)
app.include_router(settings_routes.router)
app.include_router(runs.router)
app.include_router(checkpoints.router)
app.include_router(websocket_router)


@app.on_event("startup")
async def startup():
    """Initialize application on startup."""
    init_db()
    init_tools()


@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown."""
    await close_providers()


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "MyAgent",
        "version": "1.0.0",
        "description": "Local Autonomous AI Coding Agent Platform",
        "docs": "/docs",
    }


def main():
    """Run the backend server."""
    uvicorn.run(
        "backend.app.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=True,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
